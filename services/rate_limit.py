"""
API 速率限制配置

环境变量:
- RATE_LIMIT_AUTH: 注册/登录限制，默认 "5/minute"
- RATE_LIMIT_EMAIL: 发送邮件限制，默认 "3/minute"
- RATE_LIMIT_SEARCH: 搜索接口限制，默认空（不限制）
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

RATE_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
RATE_EMAIL = os.getenv("RATE_LIMIT_EMAIL", "3/minute")
RATE_SEARCH = os.getenv("RATE_LIMIT_SEARCH", "")  # 默认不限制
