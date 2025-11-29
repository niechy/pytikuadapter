"""
鉴权服务

提供Token验证功能，支持通过环境变量控制是否启用鉴权。
"""

import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuthToken
from logger import get_logger

log = get_logger("auth")


def is_auth_enabled() -> bool:
    """
    检查是否启用鉴权

    通过环境变量 AUTH_ENABLED 控制，默认为 true（启用）
    设置为 "false" 或 "0" 可禁用鉴权
    """
    value = os.getenv("AUTH_ENABLED", "true").lower()
    return value not in ("false", "0", "no")


async def verify_token(session: AsyncSession, token: str) -> bool:
    """
    验证Token是否有效

    Args:
        session: 数据库会话
        token: 待验证的Token

    Returns:
        bool: Token是否有效
    """
    stmt = select(AuthToken).where(AuthToken.token == token)
    result = await session.execute(stmt)
    auth_token = result.scalar_one_or_none()

    if auth_token:
        log.debug(f"Token验证成功: {token[:8]}...")
        return True

    log.warning(f"Token验证失败: {token[:8]}...")
    return False


async def add_token(session: AsyncSession, token: str) -> AuthToken:
    """
    添加新Token

    Args:
        session: 数据库会话
        token: 新Token值

    Returns:
        AuthToken: 创建的Token对象
    """
    auth_token = AuthToken(token=token)
    session.add(auth_token)
    await session.flush()
    log.info(f"添加新Token: {token[:8]}...")
    return auth_token


async def delete_token(session: AsyncSession, token: str) -> bool:
    """
    删除Token

    Args:
        session: 数据库会话
        token: 待删除的Token

    Returns:
        bool: 是否删除成功
    """
    stmt = select(AuthToken).where(AuthToken.token == token)
    result = await session.execute(stmt)
    auth_token = result.scalar_one_or_none()

    if auth_token:
        await session.delete(auth_token)
        log.info(f"删除Token: {token[:8]}...")
        return True

    return False
