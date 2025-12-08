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


def _merge_config(base: dict, override: dict) -> dict:
    """
    融合两个配置，override 中的字段优先

    Args:
        base: 基础配置（来自 token 配置）
        override: 覆盖配置（来自请求）

    Returns:
        融合后的配置
    """
    merged = dict(base) if base else {}
    if override:
        merged.update(override)
    return merged


async def _resolve_providers(
    request_providers: list[Provider] | None,
    user_token: UserToken,
    session: AsyncSession
) -> list[Provider]:
    """
    解析并融合 providers 配置

    优先级规则：
    1. 请求中指定的 provider 会被使用
    2. 请求中的 config 与 token 配置融合，请求优先
    3. 请求中未指定的 provider，使用 token 配置中已启用的

    融合示例：
    - token 配置: {"key": "xxx"}
    - 请求配置: {"model": "gpt-4"}
    - 融合结果: {"key": "xxx", "model": "gpt-4"}

    如有冲突，请求配置优先。
    """
    # 获取 token 中保存的配置
    token_configs = await get_token_provider_configs(session, user_token.id)
    token_config_map = {c.provider_name: c for c in token_configs if c.enabled}

    # 如果请求中没有指定 providers，直接使用 token 配置
    if not request_providers:
        return [
            Provider(name=c.provider_name, priority=0, config=c.config_json)
            for c in token_configs if c.enabled
        ]

    # 融合请求配置和 token 配置
    merged_providers = []
    request_names = set()

    for req_provider in request_providers:
        request_names.add(req_provider.name)
        token_cfg = token_config_map.get(req_provider.name)

        if token_cfg:
            # 融合配置：token 配置为基础，请求配置覆盖
            merged_config = _merge_config(token_cfg.config_json, req_provider.config)
        else:
            # token 中没有该 provider 的配置，直接使用请求配置
            merged_config = req_provider.config or {}

        merged_providers.append(Provider(
            name=req_provider.name,
            priority=req_provider.priority,
            config=merged_config
        ))

    return merged_providers


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
