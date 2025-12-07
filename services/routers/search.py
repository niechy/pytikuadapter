"""
题库搜索路由
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from model import QuestionRequest, Provider, A
from core import construct_res
from database import get_db_session
from database.cache_service import query_cache_batch, save_cache_async
from database.models import UserToken
from services.dependencies import get_api_token
from services.auth_service import get_token_provider_configs
from providers.manager import ProvidersManager, Providersbase
from logger import get_logger

log = get_logger("search")
router = APIRouter(prefix="/v1/adapter-service", tags=["search"])

_mgr = ProvidersManager()
MAX_CONCURRENT = 20


async def _call_adapter(adapter: Providersbase, question, provider, sem: asyncio.Semaphore) -> A:
    async with sem:
        return await adapter.search(question, provider)


async def _resolve_providers(
    request_providers: list[Provider],
    user_token: UserToken,
    session: AsyncSession
) -> list[Provider]:
    """解析最终使用的 providers 列表（请求指定 > token 配置）"""
    if request_providers:
        return request_providers

    configs = await get_token_provider_configs(session, user_token.id)
    return [
        Provider(name=c.provider_name, priority=0, config=c.config_json)
        for c in configs if c.enabled
    ]


@router.post("/search")
async def search(
    request: QuestionRequest,
    session: AsyncSession = Depends(get_db_session),
    user_token: UserToken = Depends(get_api_token)
):
    """题库搜索接口"""
    providers_list = await _resolve_providers(request.providers, user_token, session)
    if not providers_list:
        raise HTTPException(status_code=400, detail="No providers specified")

    # 分离 Local 和其他 provider（Local 不走缓存逻辑，直接查询）
    local_providers = [p for p in providers_list if p.name.lower() == "local"]
    other_providers = [p for p in providers_list if p.name.lower() != "local"]

    # 批量查询缓存（仅对非 Local provider）
    cached = await query_cache_batch(session, request.query, other_providers) if other_providers else {}
    answers_from_cache = []
    providers_to_query = list(local_providers)  # Local 直接加入待查询列表

    for p in other_providers:
        if (ans := cached.get(p.name)) is not None:
            log.debug(f"缓存命中: {p.name}")
            answers_from_cache.append(ans)
        else:
            providers_to_query.append(p)

    # 并发查询
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    tasks, valid_providers = [], []

    for p in providers_to_query:
        if (adapter := _mgr.get_adapter_achieve(p.name)) is None:
            log.warning(f"未找到适配器: {p.name}")
            continue
        valid_providers.append(p)
        tasks.append(asyncio.create_task(_call_adapter(adapter, request.query, p, sem)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    answers_from_query = []
    to_cache = []

    for i, res in enumerate(results):
        p = valid_providers[i]
        if isinstance(res, Exception):
            log.error(f"异常 [{p.name}]: {type(res).__name__}: {res}")
            answers_from_query.append(A(
                provider=p.name, type=request.query.type,
                success=False, error_type="unknown", error_message=str(res)
            ))
        else:
            answers_from_query.append(res)
            if res.success:
                log.debug(f"成功 [{res.provider}]: {res.choice or res.text or res.judgement}")
                adapter = _mgr.get_adapter_achieve(p.name)
                if adapter and getattr(adapter, 'CACHEABLE', True):
                    to_cache.append((p, res))
            else:
                log.debug(f"失败 [{res.provider}]: {res.error_type}")

    # 异步写入缓存
    if to_cache:
        asyncio.create_task(save_cache_async(request.query, to_cache))

    # 构造响应
    result = construct_res(request.query, answers_from_cache + answers_from_query)
    log.info(
        f"查询: 总数={result.total_providers}, 成功={result.successful_providers}, "
        f"答案={result.unified_answer.answerKeyText or result.unified_answer.answerText or '无'}"
    )

    return JSONResponse(content=result.model_dump(exclude_none=True))
