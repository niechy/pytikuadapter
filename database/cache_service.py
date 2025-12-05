"""
缓存服务层

提供题目缓存的核心业务逻辑：
1. 批量查询多个provider的缓存答案（优化性能）
2. 异步写入/更新缓存
3. 模糊匹配查找相似题目

设计要点：
- 以provider为核心：每个provider的答案独立存储和查询
- 批量查询优化：一次查询获取多个provider的缓存，避免N次查询
- 异步写入：不阻塞主流程，后台更新缓存
- 配置感知：同一provider不同配置视为不同缓存
"""

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional, Set
import asyncio

from .models import Question, Answer, QuestionProviderAnswer
from .utils import normalize_text, normalize_options
from model import QuestionContent, Provider, A
from logger import get_logger
from services import EmbeddingService, get_embedding_service

log = get_logger("cache")

EMBEDDING_SIMILARITY_THRESHOLD = 0.82
EMBEDDING_TOP_K = 5


class CacheService:
    """
    缓存服务类

    提供题目缓存的查询、写入、更新功能。
    """

    def __init__(self, session: AsyncSession, embedding_service: Optional[EmbeddingService] = None):
        """
        初始化缓存服务

        Args:
            session: 数据库会话对象
            embedding_service: embedding服务实例，默认使用全局单例
        """
        self.session = session
        self.embedding_service = embedding_service or get_embedding_service()

    async def find_question(
        self,
        content: str,
        question_type: int,
        options: Optional[List[str]] = None
    ) -> Optional[Question]:
        """
        查找题目

        优先使用精确匹配（快速），若无匹配则回退到向量相似度匹配。

        Args:
            content: 题目内容
            question_type: 题目类型
            options: 题目选项

        Returns:
            匹配的题目对象，如果不存在则返回None
        """
        # 1. 先尝试精确匹配（快速，无需GPU计算）
        question = await self._find_by_normalized(content, question_type, options)
        if question is not None:
            return question

        # 2. 回退到向量相似度匹配
        return await self._find_by_embedding(content, question_type, options)

    async def _find_by_embedding(
        self,
        content: str,
        question_type: int,
        options: Optional[List[str]] = None
    ) -> Optional[Question]:
        """使用向量相似度查找题目"""
        if self.embedding_service is None:
            return None

        try:
            text = self._build_embedding_text(content, options)
            query_vector = await self.embedding_service.embed_query(text)
        except Exception as e:
            log.warning(f"生成查询向量失败: {e}")
            return None

        # 使用余弦距离查询最相似的题目
        normalized_options = normalize_options(options)
        distance = Question.embedding.cosine_distance(query_vector)
        stmt = (
            select(Question, distance.label("distance"))
            .where(
                and_(
                    Question.type == question_type,
                    Question.embedding.isnot(None)
                )
            )
            .order_by(distance)
            .limit(EMBEDDING_TOP_K)
        )

        result = await self.session.execute(stmt)
        for question, dist in result:
            similarity = 1 - float(dist or 0)
            if similarity >= EMBEDDING_SIMILARITY_THRESHOLD:
                # 双向校验选项一致性：两边都有选项时必须相等，一边有一边没有则不匹配
                q_has_options = question.normalized_options is not None
                req_has_options = normalized_options is not None
                if q_has_options != req_has_options:
                    continue
                if q_has_options and question.normalized_options != normalized_options:
                    continue
                log.debug(f"向量匹配成功: similarity={similarity:.4f}, question_id={question.id}")
                return question

        return None

    async def _find_by_normalized(
        self,
        content: str,
        question_type: int,
        options: Optional[List[str]] = None
    ) -> Optional[Question]:
        """使用归一化内容精确匹配查找题目（兼容旧数据）"""
        normalized_content = normalize_text(content)
        normalized_options = normalize_options(options)

        query = select(Question).where(
            and_(
                Question.normalized_content == normalized_content,
                Question.type == question_type
            )
        )

        if normalized_options is not None:
            query = query.where(Question.normalized_options == normalized_options)
        else:
            query = query.where(Question.normalized_options.is_(None))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def _build_embedding_text(self, content: str, options: Optional[List[str]]) -> str:
        """构建用于生成 embedding 的文本"""
        text = (content or "").strip()
        if options:
            valid_options = [str(opt).strip() for opt in options if opt is not None]
            if valid_options:
                option_text = " ".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(valid_options))
                text = f"{text}\n{option_text}"
        return text

    async def get_cached_answers(
        self,
        question: Question,
        provider_names: List[str]
    ) -> Dict[str, Optional[A]]:
        """
        批量获取多个provider的缓存答案（性能优化核心）

        一次查询获取指定题目在多个provider下的所有缓存答案。
        避免循环查询导致的N+1问题。

        Args:
            question: 题目对象
            provider_names: 需要查询的provider名称列表

        Returns:
            字典，key为provider名称，value为答案对象A（如果没有缓存则为None）
        """
        # 构建查询：获取该题目下所有相关provider的答案
        query = (
            select(QuestionProviderAnswer)
            .options(selectinload(QuestionProviderAnswer.answer))
            .where(
                and_(
                    QuestionProviderAnswer.question_id == question.id,
                    QuestionProviderAnswer.provider_name.in_(provider_names)
                )
            )
        )

        result = await self.session.execute(query)
        qpa_list = result.scalars().all()

        # 构建结果字典
        cached_answers: Dict[str, Optional[A]] = {name: None for name in provider_names}

        for qpa in qpa_list:
            answer = qpa.answer
            cached_answers[qpa.provider_name] = A(
                provider=qpa.provider_name,
                type=answer.type,
                choice=answer.choice,
                judgement=answer.judgement,
                text=answer.text
            )

        return cached_answers

    async def save_answer(
        self,
        query: QuestionContent,
        provider: Provider,
        answer: A
    ):
        """
        保存或更新单个provider的答案到缓存

        如果题目不存在，先创建题目。
        如果答案不存在，创建新答案。
        如果该题目-provider组合已存在，更新答案。

        Args:
            query: 题目内容对象
            provider: provider对象（包含名称和配置）
            answer: 答案对象
        """
        # 1. 查找或创建题目
        question = await self.find_question(
            content=query.content,
            question_type=query.type,
            options=query.options
        )

        if question is None:
            # 创建新题目
            embedding = await self._generate_embedding(query.content, query.options)
            question = Question(
                content=query.content,
                normalized_content=normalize_text(query.content),
                type=query.type,
                options=query.options,
                normalized_options=normalize_options(query.options),
                embedding=embedding
            )
            self.session.add(question)
            await self.session.flush()  # 获取question.id

        # 2. 查找或创建答案
        # 先查询是否已存在相同的答案（避免重复存储）
        answer_query = select(Answer).where(
            and_(
                Answer.type == answer.type,
                Answer.choice == answer.choice if answer.choice else Answer.choice.is_(None),
                Answer.judgement == answer.judgement if answer.judgement is not None else Answer.judgement.is_(None),
                Answer.text == answer.text if answer.text else Answer.text.is_(None)
            )
        )
        result = await self.session.execute(answer_query)
        answer_obj = result.scalar_one_or_none()

        if answer_obj is None:
            # 创建新答案
            answer_obj = Answer(
                type=answer.type,
                choice=answer.choice,
                judgement=answer.judgement,
                text=answer.text
            )
            self.session.add(answer_obj)
            await self.session.flush()  # 获取answer_obj.id

        # 3. 查找或创建题目-provider-答案关联
        qpa_query = select(QuestionProviderAnswer).where(
            and_(
                QuestionProviderAnswer.question_id == question.id,
                QuestionProviderAnswer.provider_name == provider.name
            )
        )
        result = await self.session.execute(qpa_query)
        qpa = result.scalar_one_or_none()

        if qpa is None:
            # 创建新关联
            qpa = QuestionProviderAnswer(
                question_id=question.id,
                provider_name=provider.name,
                answer_id=answer_obj.id
            )
            self.session.add(qpa)
        else:
            # 更新现有关联的答案
            qpa.answer_id = answer_obj.id

        await self.session.commit()

    async def batch_save_answers(
        self,
        query: QuestionContent,
        provider_answers: List[tuple[Provider, A]]
    ):
        """
        批量保存多个provider的答案（性能优化）

        Args:
            query: 题目内容对象
            provider_answers: provider和答案的元组列表 [(provider1, answer1), (provider2, answer2), ...]
        """
        # 1. 查找或创建题目（只需一次）
        question = await self.find_question(
            content=query.content,
            question_type=query.type,
            options=query.options
        )

        if question is None:
            embedding = await self._generate_embedding(query.content, query.options)
            question = Question(
                content=query.content,
                normalized_content=normalize_text(query.content),
                type=query.type,
                options=query.options,
                normalized_options=normalize_options(query.options),
                embedding=embedding
            )
            self.session.add(question)
            await self.session.flush()

        # 2. 批量处理答案
        for provider, answer in provider_answers:
            # 查找或创建答案
            answer_query = select(Answer).where(
                and_(
                    Answer.type == answer.type,
                    Answer.choice == answer.choice if answer.choice else Answer.choice.is_(None),
                    Answer.judgement == answer.judgement if answer.judgement is not None else Answer.judgement.is_(None),
                    Answer.text == answer.text if answer.text else Answer.text.is_(None)
                )
            )
            result = await self.session.execute(answer_query)
            answer_obj = result.scalar_one_or_none()

            if answer_obj is None:
                answer_obj = Answer(
                    type=answer.type,
                    choice=answer.choice,
                    judgement=answer.judgement,
                    text=answer.text
                )
                self.session.add(answer_obj)
                await self.session.flush()

            # 查找或创建关联
            qpa_query = select(QuestionProviderAnswer).where(
                and_(
                    QuestionProviderAnswer.question_id == question.id,
                    QuestionProviderAnswer.provider_name == provider.name
                )
            )
            result = await self.session.execute(qpa_query)
            qpa = result.scalar_one_or_none()

            if qpa is None:
                qpa = QuestionProviderAnswer(
                    question_id=question.id,
                    provider_name=provider.name,
                    answer_id=answer_obj.id
                )
                self.session.add(qpa)
            else:
                qpa.answer_id = answer_obj.id

        await self.session.commit()

    async def _generate_embedding(
        self,
        content: str,
        options: Optional[List[str]] = None
    ) -> Optional[List[float]]:
        """为新题目生成 embedding 向量（使用 passage 编码）"""
        if self.embedding_service is None:
            return None
        try:
            text = self._build_embedding_text(content, options)
            return await self.embedding_service.embed_passage(text)
        except Exception as e:
            log.warning(f"生成embedding失败: {e}")
            return None


async def query_cache_batch(
    session: AsyncSession,
    query: QuestionContent,
    providers: List[Provider]
) -> Dict[str, Optional[A]]:
    """
    批量查询缓存的便捷函数

    Args:
        session: 数据库会话
        query: 题目内容
        providers: provider列表

    Returns:
        字典，key为provider名称，value为缓存的答案（没有缓存则为None）
    """
    cache_service = CacheService(session)

    # 查找题目
    question = await cache_service.find_question(
        content=query.content,
        question_type=query.type,
        options=query.options
    )

    if question is None:
        # 题目不存在，返回空缓存
        return {p.name: None for p in providers}

    # 批量查询缓存
    provider_names = [p.name for p in providers]

    return await cache_service.get_cached_answers(
        question=question,
        provider_names=provider_names
    )


async def save_cache_async(
    query: QuestionContent,
    provider_answers: List[tuple[Provider, A]]
):
    """
    异步保存缓存（后台任务）

    不阻塞主流程，在后台异步写入缓存。
    使用独立的数据库会话，避免影响主流程。

    Args:
        query: 题目内容
        provider_answers: provider和答案的元组列表
    """
    from .config import db_manager

    try:
        async with db_manager.get_session() as session:
            cache_service = CacheService(session)
            await cache_service.batch_save_answers(query, provider_answers)
    except Exception as e:
        # 缓存写入失败不应该影响主流程，只记录日志
        log.error(f"缓存写入失败: {e}")
