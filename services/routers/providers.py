from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from database.models import UserToken
from services.schemas import (
    ProviderConfigRead, ProviderConfigUpdate, ProviderConfigBatchUpdate,
    ProviderInfo, ProviderConfigField
)
from services.auth_service import get_token_provider_configs, upsert_provider_config
from services.dependencies import get_current_user
from services.provider_order import get_ordered_providers
from providers.manager import ProvidersManager

router = APIRouter(prefix="/api/providers", tags=["题库Provider"])
token_router = APIRouter(prefix="/api/tokens/{token_id}/providers", tags=["题库Provider配置"])

_mgr = ProvidersManager()


def _extract_config_fields(configs_cls) -> list[ProviderConfigField]:
    """从Pydantic模型提取配置字段信息"""
    fields = []
    for name, field_info in configs_cls.model_fields.items():
        field_type = "string"
        annotation = field_info.annotation
        if annotation is bool:
            field_type = "boolean"
        elif annotation is int:
            field_type = "integer"

        fields.append(ProviderConfigField(
            name=name,
            type=field_type,
            title=field_info.title or name,
            description=field_info.description,
            required=field_info.is_required(),
            default=field_info.default if field_info.default is not None else None
        ))
    return fields


@router.get("/available", response_model=list[ProviderInfo], summary="获取可用Provider列表")
async def list_available_providers():
    """获取系统支持的所有题库Provider及其配置字段说明"""
    providers = []
    for p in get_ordered_providers():
        adapter = _mgr.get_adapter(p["name"])
        if not adapter:
            continue

        config_fields = []
        if hasattr(adapter, 'Configs'):
            config_fields = _extract_config_fields(adapter.Configs)

        providers.append(ProviderInfo(
            name=p["name"],
            home=p.get("home"),
            free=p.get("free", False),
            pay=p.get("pay", False),
            config_fields=config_fields
        ))
    return providers


# ========== Token Provider Config Routes ==========

def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


async def verify_token_ownership(session: AsyncSession, token_id: int, user_id: int) -> UserToken:
    result = await session.execute(
        select(UserToken).where(UserToken.id == token_id, UserToken.user_id == user_id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@token_router.get("", response_model=list[ProviderConfigRead], summary="获取Provider配置列表")
async def list_provider_configs(
    token_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """获取指定Token下的所有题库Provider配置"""
    await verify_token_ownership(session, token_id, current_user.id)
    configs = await get_token_provider_configs(session, token_id)
    return [
        ProviderConfigRead(
            id=c.id,
            provider_name=c.provider_name,
            api_key_preview=mask_api_key(c.api_key),
            config_json=c.config_json,
            enabled=c.enabled
        )
        for c in configs
    ]


@token_router.put("", response_model=list[ProviderConfigRead], summary="批量更新Provider配置")
async def update_provider_configs(
    token_id: int,
    data: ProviderConfigBatchUpdate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """批量更新指定Token下的题库Provider配置。如果配置不存在则创建。"""
    await verify_token_ownership(session, token_id, current_user.id)

    results = []
    for config_update in data.configs:
        config = await upsert_provider_config(
            session,
            token_id,
            config_update.provider_name,
            config_update.api_key,
            config_update.config_json,
            config_update.enabled
        )
        results.append(ProviderConfigRead(
            id=config.id,
            provider_name=config.provider_name,
            api_key_preview=mask_api_key(config.api_key),
            config_json=config.config_json,
            enabled=config.enabled
        ))

    await session.commit()
    return results
