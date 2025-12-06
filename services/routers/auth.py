from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.schemas import (
    UserCreate, UserLogin, UserPublic, TokenResponse, RegisterResponse,
    EmailVerifyRequest, AuthConfigResponse, ResendVerificationRequest
)
from services.auth_service import (
    get_user_by_username, get_user_by_email, create_user, authenticate_user,
    create_access_token, decode_access_token, get_user_by_id,
    is_email_verification_required, ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.email_service import (
    create_verification_code, send_verification_email, verify_code_by_email
)
from services.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.get("/config", response_model=AuthConfigResponse, summary="获取认证配置")
async def get_auth_config():
    """获取系统认证配置，如是否需要邮箱验证等"""
    return AuthConfigResponse(email_verification_required=is_email_verification_required())


@router.post("/register", response_model=RegisterResponse, summary="用户注册")
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """注册新用户。如果系统开启了邮箱验证，会自动发送验证邮件。"""
    if await get_user_by_username(session, data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if await get_user_by_email(session, data.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    user = await create_user(session, data.username, data.email, data.password)
    await session.commit()

    email_required = is_email_verification_required()
    if email_required:
        code = await create_verification_code(session, user.id)
        await session.commit()
        if not await send_verification_email(user.email, code):
            raise HTTPException(status_code=500, detail="Failed to send verification email")

    return RegisterResponse(
        user=UserPublic.model_validate(user),
        email_verification_required=email_required
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_db_session)
):
    """用户登录，返回JWT访问令牌。如果系统开启了邮箱验证且用户未验证，返回403。"""
    user = await authenticate_user(session, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if is_email_verification_required() and not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", summary="用户登出")
async def logout():
    """用户登出。JWT无状态，客户端删除token即可。"""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserPublic, summary="获取当前用户信息")
async def get_me(current_user=Depends(get_current_user)):
    """获取当前登录用户的信息"""
    return UserPublic.model_validate(current_user)


@router.post("/verify-email", summary="验证邮箱")
async def verify_email(
    data: EmailVerifyRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """使用邮箱和验证码验证邮箱（无需登录）"""
    if not await verify_code_by_email(session, data.email, data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    await session.commit()
    return {"message": "Email verified successfully"}


@router.post("/verify-email/resend", summary="重发验证邮件")
async def resend_verification(
    data: ResendVerificationRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """重新发送邮箱验证邮件（无需登录）"""
    user = await get_user_by_email(session, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified:
        return {"message": "Email already verified"}

    code = await create_verification_code(session, user.id)
    await session.commit()

    if not await send_verification_email(user.email, code):
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"message": "Verification email sent"}
