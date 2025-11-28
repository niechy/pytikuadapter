import asyncio
from contextlib import asynccontextmanager

from aiohttp import ClientResponseError
from fastapi import FastAPI, Header, Depends, HTTPException
from pydantic import ValidationError

from model import QuestionRequest, Res, Provider, A
import providers.manager as manager
from core import construct_res
import uvicorn
from database import init_database, close_database, get_db_session
from database.cache_service import query_cache_batch, save_cache_async
from sqlalchemy.ext.asyncio import AsyncSession

mgr = manager.ProvidersManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 初始化数据库连接和表结构
    2. 初始化aiohttp会话
    3. 显示可用的适配器列表

    关闭时：
    1. 关闭aiohttp会话
    2. 关闭数据库连接
    """
    print("正在初始化数据库...")
    await init_database()
    print("数据库初始化完成")

    print("当前适配器列表：", mgr.available_plugins())
    await manager.Providersbase.init_session()

    yield

    await manager.Providersbase.close_session()
    await close_database()
    print("应用已关闭")


app = FastAPI(lifespan=lifespan)


def get_api_key(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ", 1)[1]
    return token


MAX_CONCURRENT = 20


async def _call_adapter(ad, question, provider, sem: asyncio.Semaphore):
    """
    在信号量保护下调用单个 providers.search，捕获异常并返回统一结构。
    """
    async with sem:
        return await ad.search(question, provider)


@app.post("/v1/adapter-service/search")
async def search(
    _search_request: QuestionRequest,
    api_key: str = Depends(get_api_key),
    session: AsyncSession = Depends(get_db_session)
):
    """
    题目搜索接口

    流程：
    1. 批量查询缓存（一次查询获取所有provider的缓存）
    2. 对于有缓存的provider：
       - 如果请求中包含该provider，使用缓存答案
       - 如果请求中不包含该provider，忽略缓存
    3. 对于没有缓存的provider，调用实际的adapter查询
    4. 异步写入新的答案到缓存（不阻塞响应）
    5. 返回聚合结果

    Args:
        _search_request: 搜索请求，包含题目和provider列表
        api_key: API密钥（用于鉴权）
        session: 数据库会话（依赖注入）

    Returns:
        Res: 聚合后的搜索结果
    """
    # 1. 批量查询缓存
    cached_answers = await query_cache_batch(
        session=session,
        query=_search_request.query,
        providers=_search_request.providers
    )

    # 2. 分离有缓存和无缓存的provider
    providers_to_query = []  # 需要实际查询的provider
    answers_from_cache = []  # 从缓存获取的答案
    requested_provider_names = {p.name for p in _search_request.providers}

    for provider in _search_request.providers:
        cached_answer = cached_answers.get(provider.name)

        if cached_answer is not None:
            # 有缓存，直接使用
            print(f"缓存命中: {provider.name}")
            answers_from_cache.append(cached_answer)
        else:
            # 无缓存，需要查询
            providers_to_query.append(provider)

    # 3. 并发查询没有缓存的provider
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = []

    for provider in providers_to_query:
        adapter = mgr.get_adapter_achieve(provider.name)
        if adapter is None:
            print(f"警告: 未找到适配器 {provider.name}")
            continue

        # create_task 立即调度，但实际并发由 sem 控制
        tasks.append(
            asyncio.create_task(
                _call_adapter(adapter, _search_request.query, provider, sem)
            )
        )

    # 等待所有查询完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. 处理查询结果
    answers_from_query = []  # 从实际查询获取的答案
    provider_answer_pairs = []  # 用于异步写入缓存的数据

    for i, res in enumerate(results):
        provider = providers_to_query[i]

        if isinstance(res, Exception):
            # 发生了未捕获的异常（理论上不应该发生，因为provider内部应该捕获所有异常）
            print(f"⚠️  未捕获异常 [{provider.name}]: {type(res).__name__}: {res}")
            # 创建一个失败的答案对象
            error_answer = A(
                provider=provider.name,
                type=_search_request.query.type,
                success=False,
                error_type="unknown",
                error_message=f"未捕获异常: {str(res)}"
            )
            answers_from_query.append(error_answer)
        else:
            # 正常返回的 A 对象
            if res.success:
                print(f"✅ 成功 [{res.provider}]: {res.choice or res.text or res.judgement}")
                # 只有成功的答案才写入缓存
                provider_answer_pairs.append((provider, res))
            else:
                print(f"❌ 失败 [{res.provider}]: {res.error_type} - {res.error_message}")

            answers_from_query.append(res)

    # 5. 合并缓存答案和查询答案
    all_answers = answers_from_cache + answers_from_query

    # 6. 异步写入缓存（不阻塞响应）
    if provider_answer_pairs:
        asyncio.create_task(
            save_cache_async(_search_request.query, provider_answer_pairs)
        )

    # 7. 构造并返回响应
    result = construct_res(_search_request.query, all_answers)

    # 输出统计信息
    print(f"\n📊 查询统计:")
    print(f"   总provider数: {result.total_providers}")
    print(f"   ✅ 成功: {result.successful_providers}")
    print(f"   ❌ 失败: {result.failed_providers}")
    print(f"   最终答案: {result.unified_answer.answerKeyText or result.unified_answer.answerText or '无'}")

    return result


if __name__ == '__main__':
    uvicorn.run('demo:app', host="127.0.0.1", port=8060, log_level='info')
    # uvicorn demo:app --host 0.0.0.0 --port 8060 --workers 4 --log-level info
