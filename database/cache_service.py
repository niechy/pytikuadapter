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
from .utils import normalize_text, normalize_options, compute_config_hash
from model import QuestionContent, Provider, A
from logger import get_logger

log = get_logger("cache")


class CacheService:
    """
    缓存服务类

    提供题目缓存的查询、写入、更新功能。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化缓存服务

        Args:
            session: 数据库会话对象
        """
        self.session = session

    async def find_question(
        self,
        content: str,
        question_type: int,
        options: Optional[List[str]] = None
    ) -> Optional[Question]:
        """
        查找题目（精确匹配归一化内容）

        使用归一化的题目内容和选项进行匹配。

        Args:
            content: 题目内容
            question_type: 题目类型
            options: 题目选项

        Returns:
            匹配的题目对象，如果不存在则返回None
        """
        # 归一化题目内容和选项
        normalized_content = normalize_text(content)
        normalized_options = normalize_options(options)

        # 构建查询条件
        query = select(Question).where(
            and_(
                Question.normalized_content == normalized_content,
                Question.type == question_type
            )
        )

        # 如果有选项，加入选项匹配条件
        if normalized_options is not None:
            query = query.where(Question.normalized_options == normalized_options)
        else:
            query = query.where(Question.normalized_options.is_(None))

        # 执行查询
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_cached_answers(
        self,
        question: Question,
        provider_names: List[str],
        provider_configs: Dict[str, Dict]
    ) -> Dict[str, Optional[A]]:
        """
        批量获取多个provider的缓存答案（性能优化核心）

        一次查询获取指定题目在多个provider下的所有缓存答案。
        避免循环查询导致的N+1问题。

        Args:
            question: 题目对象
            provider_names: 需要查询的provider名称列表
            provider_configs: provider配置字典，key为provider名称，value为配置dict

        Returns:
            字典，key为provider名称，value为答案对象A（如果没有缓存则为None）

        Example:
            {
                "Like知识库": A(provider="Like知识库", choice=["A"], type=0),
                "万能题库": None,  # 没有缓存
            }
        """
        # 计算每个provider的配置哈希
        config_hashes = {
            name: compute_config_hash(provider_configs.get(name, {}))
            for name in provider_names
        }

        # 构建查询：获取该题目下所有相关provider的答案
        # 使用 selectinload 预加载关联的 answer 对象，避免N+1查询
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
            # 检查配置哈希是否匹配
            expected_hash = config_hashes.get(qpa.provider_name)
            if qpa.config_hash != expected_hash:
                # 配置不匹配，跳过（视为没有缓存）
                continue

            # 将数据库答案转换为模型A
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
            question = Question(
                content=query.content,
                normalized_content=normalize_text(query.content),
                type=query.type,
                options=query.options,
                normalized_options=normalize_options(query.options)
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
        config_hash = compute_config_hash(provider.config)

        qpa_query = select(QuestionProviderAnswer).where(
            and_(
                QuestionProviderAnswer.question_id == question.id,
                QuestionProviderAnswer.provider_name == provider.name,
                QuestionProviderAnswer.config_hash == config_hash
            )
        )
        result = await self.session.execute(qpa_query)
        qpa = result.scalar_one_or_none()

        if qpa is None:
            # 创建新关联
            qpa = QuestionProviderAnswer(
                question_id=question.id,
                provider_name=provider.name,
                answer_id=answer_obj.id,
                config_hash=config_hash
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
            question = Question(
                content=query.content,
                normalized_content=normalize_text(query.content),
                type=query.type,
                options=query.options,
                normalized_options=normalize_options(query.options)
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
            config_hash = compute_config_hash(provider.config)

            qpa_query = select(QuestionProviderAnswer).where(
                and_(
                    QuestionProviderAnswer.question_id == question.id,
                    QuestionProviderAnswer.provider_name == provider.name,
                    QuestionProviderAnswer.config_hash == config_hash
                )
            )
            result = await self.session.execute(qpa_query)
            qpa = result.scalar_one_or_none()

            if qpa is None:
                qpa = QuestionProviderAnswer(
                    question_id=question.id,
                    provider_name=provider.name,
                    answer_id=answer_obj.id,
                    config_hash=config_hash
                )
                self.session.add(qpa)
            else:
                qpa.answer_id = answer_obj.id

        await self.session.commit()


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
    provider_configs = {p.name: p.config for p in providers}

    return await cache_service.get_cached_answers(
        question=question,
        provider_names=provider_names,
        provider_configs=provider_configs
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
