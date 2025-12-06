from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.schemas import UserTokenCreate, UserTokenRead, UserTokenCreated
from services.auth_service import get_user_tokens, create_user_token, delete_user_token
from services.dependencies import get_current_user

router = APIRouter(prefix="/api/tokens", tags=["API Token"])


def mask_token(token: str) -> str:
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}...{token[-4:]}"


@router.get("", response_model=list[UserTokenRead], summary="获取Token列表")
async def list_tokens(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """获取当前用户的所有API Token"""
    tokens = await get_user_tokens(session, current_user.id)
    return [
        UserTokenRead(
            id=t.id,
            name=t.name,
            token_preview=mask_token(t.token),
            created_at=t.created_at,
            last_used_at=t.last_used_at
        )
        for t in tokens
    ]


@router.post("", response_model=UserTokenCreated, status_code=201, summary="创建Token")
async def create_token(
    data: UserTokenCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """创建新的API Token。完整Token仅在创建时返回一次，请妥善保存。"""
    token = await create_user_token(session, current_user.id, data.name)
    await session.commit()
    return UserTokenCreated(
        id=token.id,
        name=token.name,
        token=token.token,
        created_at=token.created_at
    )


@router.delete("/{token_id}", summary="删除Token")
async def delete_token(
    token_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """删除指定的API Token"""
    if not await delete_user_token(session, current_user.id, token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    await session.commit()
    return {"message": "Token deleted"}
