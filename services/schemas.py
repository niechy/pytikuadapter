from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ========== Auth Schemas ==========
class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserPublic(BaseModel):
    """用户公开信息"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    email_verified: bool = Field(..., description="邮箱是否已验证")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class RegisterResponse(BaseModel):
    """注册成功响应"""
    user: UserPublic = Field(..., description="用户信息")
    email_verification_required: bool = Field(..., description="是否需要邮箱验证")


class AuthConfigResponse(BaseModel):
    """认证配置响应"""
    email_verification_required: bool = Field(..., description="是否需要邮箱验证")


# ========== User Token Schemas ==========
class UserTokenCreate(BaseModel):
    """创建API Token请求"""
    name: str = Field(..., min_length=1, max_length=100, description="Token名称")


class UserTokenRead(BaseModel):
    """API Token信息"""
    id: int = Field(..., description="Token ID")
    name: str = Field(..., description="Token名称")
    token_preview: str = Field(..., description="Token预览（仅显示前后几位）")
    created_at: datetime = Field(..., description="创建时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")

    model_config = {"from_attributes": True}


class UserTokenCreated(BaseModel):
    """Token创建成功响应"""
    id: int = Field(..., description="Token ID")
    name: str = Field(..., description="Token名称")
    token: str = Field(..., description="完整Token（仅创建时返回，请妥善保存）")
    created_at: datetime = Field(..., description="创建时间")


# ========== Provider Config Schemas ==========
class ProviderConfigRead(BaseModel):
    """题库Provider配置信息"""
    id: int = Field(..., description="配置ID")
    provider_name: str = Field(..., description="Provider名称")
    api_key_preview: Optional[str] = Field(None, description="API Key预览")
    config_json: dict[str, Any] = Field(..., description="配置JSON")
    enabled: bool = Field(..., description="是否启用")

    model_config = {"from_attributes": True}


class ProviderConfigUpdate(BaseModel):
    """更新Provider配置请求"""
    provider_name: str = Field(..., description="Provider名称")
    api_key: Optional[str] = Field(None, description="API Key")
    config_json: Optional[dict[str, Any]] = Field(None, description="配置JSON")
    enabled: Optional[bool] = Field(None, description="是否启用")


class ProviderConfigBatchUpdate(BaseModel):
    """批量更新Provider配置请求"""
    configs: list[ProviderConfigUpdate] = Field(..., description="配置列表")


# ========== Email Verification ==========
class EmailVerifyRequest(BaseModel):
    """邮箱验证请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., description="验证码")


class ResendVerificationRequest(BaseModel):
    """重发验证邮件请求"""
    email: EmailStr = Field(..., description="邮箱地址")


# ========== Provider Info ==========
class ProviderConfigField(BaseModel):
    """Provider配置字段定义"""
    name: str = Field(..., description="字段名")
    type: str = Field(..., description="字段类型")
    title: str = Field(..., description="字段标题")
    description: Optional[str] = Field(None, description="字段描述")
    required: bool = Field(..., description="是否必填")
    default: Optional[Any] = Field(None, description="默认值")


class ProviderInfo(BaseModel):
    """可用的Provider信息"""
    name: str = Field(..., description="Provider名称（唯一标识）")
    home: Optional[str] = Field(None, description="Provider官网")
    free: bool = Field(..., description="是否有免费额度")
    pay: bool = Field(..., description="是否支持付费")
    config_fields: list[ProviderConfigField] = Field(..., description="配置字段列表")
