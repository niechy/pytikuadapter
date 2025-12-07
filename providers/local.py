"""
Local缓存适配器

从本地数据库缓存中查询答案，不进行网络请求。
"""

from .manager import Providersbase
from model import QuestionContent, Provider, A
from database.cache_service import CacheService
from database.config import db_manager


class Local(Providersbase):
    """
    Local缓存适配器

    从本地数据库缓存中查询答案。
    这个适配器不会进行网络请求，只返回已缓存的数据。
    只要 provider 列表中包含 Local 就会被调用。
    """

    name = "Local"
    home = "本地缓存"
    FREE = True
    PAY = False
    CACHEABLE = False  # 本地缓存适配器的答案不需要再存入缓存

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """
        从本地缓存查询答案

        Args:
            query: 题目内容
            provider: provider配置

        Returns:
            A: 统一的答案对象
            - 缓存命中：返回成功的答案
            - 缓存未命中：返回失败，error_type="cache_miss"
        """
        try:
            # 获取数据库会话
            async with db_manager.get_session() as session:
                cache_service = CacheService(session)

                # 查找题目
                question = await cache_service.find_question(
                    content=query.content,
                    question_type=query.type,
                    options=query.options
                )

                if question is None:
                    # 题目不存在于缓存中
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="cache_miss",
                        error_message="缓存中未找到该题目"
                    )

                # 查询该题目的所有缓存答案
                # 返回任意一个可用的缓存答案（不限于 Local 自己的）
                from sqlalchemy import select
                from database.models import QuestionProviderAnswer

                query_all = (
                    select(QuestionProviderAnswer)
                    .where(QuestionProviderAnswer.question_id == question.id)
                    .limit(1)
                )

                result = await session.execute(query_all)
                qpa = result.scalar_one_or_none()

                if qpa is None:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="cache_miss",
                        error_message="缓存中未找到答案"
                    )

                # 加载关联的答案对象
                await session.refresh(qpa, ['answer'])
                answer = qpa.answer

                # 返回答案（标记为Local提供）
                return A(
                    provider=self.name,
                    type=answer.type,
                    choice=answer.choice,
                    judgement=answer.judgement,
                    text=answer.text,
                    success=True
                )

        except Exception as e:
            # 缓存查询失败
            return A(
                provider=self.name,
                type=query.type,
                success=False,
                error_type="unknown",
                error_message=f"缓存查询失败: {str(e)}"
            )
