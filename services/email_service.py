import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, EmailVerificationCode
from logger import get_logger

log = get_logger("email_service")


def get_email_config() -> dict:
    return {
        "from_address": os.getenv("EMAIL_FROM_ADDRESS", "tikuadapter@mail.ncy.asia"),
        "from_alias": os.getenv("EMAIL_FROM_ALIAS", "TikuAdapter"),
    }


def _create_dm_client():
    """创建阿里云邮件服务客户端（使用默认凭据链）"""
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_dm20151123.client import Client as DmClient

    cred_client = CredentialClient()

    api_config = open_api_models.Config(credential=cred_client)
    api_config.endpoint = 'dm.aliyuncs.com'

    return DmClient(api_config)


async def send_verification_email(to_email: str, code: str, purpose: str = "verify") -> bool:
    """发送验证邮件

    Args:
        to_email: 收件人邮箱
        code: 验证码
        purpose: 用途，"verify" 为邮箱验证，"reset_password" 为重置密码
    """
    from alibabacloud_dm20151123 import models as dm_models
    from alibabacloud_tea_util import models as util_models

    config = get_email_config()

    if purpose == "reset_password":
        subject = "TikuAdapter 重置密码"
        title = "重置密码"
        hint = "如果您没有请求重置密码，请忽略此邮件。"
    else:
        subject = "TikuAdapter 邮箱验证"
        title = "邮箱验证"
        hint = "如果您没有注册 TikuAdapter，请忽略此邮件。"

    try:
        client = _create_dm_client()
        request = dm_models.SingleSendMailRequest(
            address_type=1,
            account_name=config["from_address"],
            from_alias=config["from_alias"],
            reply_to_address=False,
            to_address=to_email,
            subject=subject,
            html_body=f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>{title}</h2>
                <p>您的验证码是：</p>
                <p style="font-size: 24px; font-weight: bold; color: #4F46E5; letter-spacing: 4px;">{code}</p>
                <p>验证码有效期为 15 分钟。</p>
                <p style="color: #666; font-size: 12px;">{hint}</p>
            </div>
            """
        )
        runtime = util_models.RuntimeOptions()
        await client.single_send_mail_with_options_async(request, runtime)
        log.info(f"Verification email ({purpose}) sent to {to_email}")
        return True
    except Exception as e:
        log.error(f"Failed to send email to {to_email}: {e}")
        return False


def generate_verification_code() -> str:
    return secrets.token_hex(3).upper()  # 6位十六进制


async def create_verification_code(session: AsyncSession, user_id: int) -> str:
    """创建验证码"""
    # 删除旧验证码
    result = await session.execute(
        select(EmailVerificationCode).where(EmailVerificationCode.user_id == user_id)
    )
    for old_code in result.scalars().all():
        await session.delete(old_code)

    code = generate_verification_code()
    verification = EmailVerificationCode(
        user_id=user_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    session.add(verification)
    await session.flush()
    return code


async def verify_code_by_email(session: AsyncSession, email: str, code: str) -> bool:
    """通过邮箱和验证码验证"""
    # 先找到用户
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        return False

    # 查找验证码
    result = await session.execute(
        select(EmailVerificationCode).where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.code == code.upper()
        )
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return False

    if verification.expires_at < datetime.utcnow():
        await session.delete(verification)
        return False

    # 验证成功，删除验证码并更新用户状态
    await session.delete(verification)
    user.email_verified = True

    await session.flush()
    log.info(f"Email verified for user {user.id}")
    return True


async def reset_password_by_email(session: AsyncSession, email: str, code: str, new_password: str) -> bool:
    """通过邮箱和验证码重置密码"""
    import bcrypt

    # 先找到用户
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        return False

    # 查找验证码
    result = await session.execute(
        select(EmailVerificationCode).where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.code == code.upper()
        )
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return False

    if verification.expires_at < datetime.utcnow():
        await session.delete(verification)
        return False

    # 验证成功，删除验证码并更新密码
    await session.delete(verification)
    user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    await session.flush()
    log.info(f"Password reset for user {user.id}")
    return True
