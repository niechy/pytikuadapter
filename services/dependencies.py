from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from database.models import User, UserToken
from services.auth_service import decode_access_token, get_user_by_id, get_user_token_by_value, update_token_last_used


async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """验证 JWT Token，获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_id(session, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_api_token(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserToken:
    """验证 API Token（用于 search 接口）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if authorization.startswith("Bearer "):
        token_value = authorization.split(" ", 1)[1]
    elif authorization.startswith("ApiKey "):
        token_value = authorization.split(" ", 1)[1]
    else:
        token_value = authorization

    user_token = await get_user_token_by_value(session, token_value)
    if not user_token or not user_token.user.is_active:
        raise HTTPException(status_code=401, detail="Invalid API token")

    await update_token_last_used(session, user_token)
    return user_token
