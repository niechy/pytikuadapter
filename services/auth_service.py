import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserToken, TokenProviderConfig
from logger import get_logger

log = get_logger("auth_service")


def _get_or_create_secret_key() -> str:
    """获取或自动生成 JWT 密钥，持久化到 data/.jwt_secret"""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    secret_file = data_dir / ".jwt_secret"

    if secret_file.exists():
        return secret_file.read_text().strip()

    # 首次运行，自动生成
    key = secrets.token_urlsafe(32)
    secret_file.write_text(key)
    log.info(f"Generated new JWT secret key: {secret_file}")
    return key


# JWT config
SECRET_KEY = _get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def is_email_verification_required() -> bool:
    return os.getenv("EMAIL_VERIFICATION_REQUIRED", "false").lower() in ("true", "1", "yes")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, username: str, email: str, password: str) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        email_verified=not is_email_verification_required()
    )
    session.add(user)
    await session.flush()
    log.info(f"Created user: {username}")
    return user


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(session, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


# ========== User Token Management ==========
def generate_api_token() -> str:
    return secrets.token_urlsafe(32)


async def get_user_tokens(session: AsyncSession, user_id: int) -> list[UserToken]:
    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user_id).order_by(UserToken.created_at.desc())
    )
    return list(result.scalars().all())


async def create_user_token(session: AsyncSession, user_id: int, name: str) -> UserToken:
    token = UserToken(user_id=user_id, name=name, token=generate_api_token())
    session.add(token)
    await session.flush()
    log.info(f"Created token '{name}' for user {user_id}")
    return token


async def delete_user_token(session: AsyncSession, user_id: int, token_id: int) -> bool:
    result = await session.execute(
        select(UserToken).where(UserToken.id == token_id, UserToken.user_id == user_id)
    )
    token = result.scalar_one_or_none()
    if token:
        await session.delete(token)
        log.info(f"Deleted token {token_id} for user {user_id}")
        return True
    return False


async def get_user_token_by_value(session: AsyncSession, token_value: str) -> Optional[UserToken]:
    result = await session.execute(select(UserToken).where(UserToken.token == token_value))
    return result.scalar_one_or_none()


async def update_token_last_used(session: AsyncSession, token: UserToken):
    token.last_used_at = datetime.now(timezone.utc)
    await session.flush()


# ========== Provider Config Management ==========
async def get_token_provider_configs(session: AsyncSession, token_id: int) -> list[TokenProviderConfig]:
    result = await session.execute(
        select(TokenProviderConfig).where(TokenProviderConfig.token_id == token_id)
    )
    return list(result.scalars().all())


async def upsert_provider_config(
    session: AsyncSession,
    token_id: int,
    provider_name: str,
    api_key: Optional[str] = None,
    config_json: Optional[dict] = None,
    enabled: Optional[bool] = None
) -> TokenProviderConfig:
    result = await session.execute(
        select(TokenProviderConfig).where(
            TokenProviderConfig.token_id == token_id,
            TokenProviderConfig.provider_name == provider_name
        )
    )
    config = result.scalar_one_or_none()

    if config:
        if api_key is not None:
            config.api_key = api_key
        if config_json is not None:
            config.config_json = config_json
        if enabled is not None:
            config.enabled = enabled
    else:
        config = TokenProviderConfig(
            token_id=token_id,
            provider_name=provider_name,
            api_key=api_key or "",
            config_json=config_json or {},
            enabled=enabled if enabled is not None else True
        )
        session.add(config)

    await session.flush()
    return config
