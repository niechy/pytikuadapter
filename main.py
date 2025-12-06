from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from model import QuestionRequest, Provider, A
import providers.manager as manager
from core import construct_res
import uvicorn
from database import init_database, close_database, get_db_session
from database.cache_service import query_cache_batch, save_cache_async
from database.models import UserToken
from services.dependencies import get_api_token
from services.auth_service import get_token_provider_configs
from services.routers import auth_router, tokens_router, providers_router, providers_token_router
from logger import get_logger

log = get_logger("main")

mgr = manager.ProvidersManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("正在初始化数据库...")
    await init_database()
    log.info("数据库初始化完成")

    log.info(f"当前适配器列表: {mgr.available_plugins()}")
    await manager.Providersbase.init_session()

    yield

    await manager.Providersbase.close_session()
    await close_database()
    log.info("应用已关闭")


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(tokens_router)
app.include_router(providers_router)
app.include_router(providers_token_router)


MAX_CONCURRENT = 20


async def _call_adapter(ad, question, provider, sem: asyncio.Semaphore):
    async with sem:
        return await ad.search(question, provider)


async def resolve_providers(
    request_providers: list[Provider],
    user_token: UserToken,
    session: AsyncSession
) -> list[Provider]:
    """
    解析最终使用的 providers 列表

    优先级：
    1. 如果请求中指定了 providers，使用请求中的
    2. 如果请求中没有指定但有 token 配置，使用 token 配置
    """
    if request_providers:
        return request_providers

    # 从 token 配置中获取 providers
    configs = await get_token_provider_configs(session, user_token.id)
    providers = []
    for config in configs:
        if config.enabled:
            providers.append(Provider(
                name=config.provider_name,
                priority=0,
                config=config.config_json
            ))
    return providers


@app.post("/v1/adapter-service/search")
async def search(
    _search_request: QuestionRequest,
    session: AsyncSession = Depends(get_db_session),
    user_token: UserToken = Depends(get_api_token)
):
    # 解析 providers
    providers_list = await resolve_providers(
        _search_request.providers,
        user_token,
        session
    )

    if not providers_list:
        raise HTTPException(status_code=400, detail="No providers specified")

    # 1. 批量查询缓存
    cached_answers = await query_cache_batch(
        session=session,
        query=_search_request.query,
        providers=providers_list
    )

    # 2. 分离有缓存和无缓存的provider
    providers_to_query = []
    answers_from_cache = []

    for provider in providers_list:
        cached_answer = cached_answers.get(provider.name)
        if cached_answer is not None:
            log.debug(f"缓存命中: {provider.name}")
            answers_from_cache.append(cached_answer)
        else:
            providers_to_query.append(provider)

    # 3. 并发查询没有缓存的provider
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = []
    valid_providers = []

    for provider in providers_to_query:
        adapter = mgr.get_adapter_achieve(provider.name)
        if adapter is None:
            log.warning(f"未找到适配器 {provider.name}")
            continue

        valid_providers.append(provider)
        tasks.append(
            asyncio.create_task(
                _call_adapter(adapter, _search_request.query, provider, sem)
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. 处理查询结果
    answers_from_query = []
    provider_answer_pairs = []

    for i, res in enumerate(results):
        provider = valid_providers[i]

        if isinstance(res, Exception):
            log.error(f"未捕获异常 [{provider.name}]: {type(res).__name__}: {res}")
            error_answer = A(
                provider=provider.name,
                type=_search_request.query.type,
                success=False,
                error_type="unknown",
                error_message=f"未捕获异常: {str(res)}"
            )
            answers_from_query.append(error_answer)
        else:
            if res.success:
                log.debug(f"成功 [{res.provider}]: {res.choice or res.text or res.judgement}")
                adapter = mgr.get_adapter_achieve(provider.name)
                if adapter and getattr(adapter, 'CACHEABLE', True):
                    provider_answer_pairs.append((provider, res))
            else:
                log.debug(f"失败 [{res.provider}]: {res.error_type} - {res.error_message}")

            answers_from_query.append(res)

    # 5. 合并缓存答案和查询答案
    all_answers = answers_from_cache + answers_from_query

    # 6. 异步写入缓存
    if provider_answer_pairs:
        asyncio.create_task(
            save_cache_async(_search_request.query, provider_answer_pairs)
        )

    # 7. 构造并返回响应
    result = construct_res(_search_request.query, all_answers)

    log.info(
        f"查询统计: 总数={result.total_providers}, "
        f"成功={result.successful_providers}, 失败={result.failed_providers}, "
        f"答案={result.unified_answer.answerKeyText or result.unified_answer.answerText or '无'}"
    )

    return JSONResponse(content=result.model_dump(exclude_none=True))


if __name__ == '__main__':
    uvicorn.run('main:app', host="127.0.0.1", port=8060, log_level='info')
