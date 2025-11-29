"""
数据库模块

提供数据库模型、配置、工具函数和缓存服务。
"""

from .models import Question, Answer, QuestionProviderAnswer, Base
from .config import (
    DatabaseConfig,
    DatabaseManager,
    db_manager,
    init_database,
    close_database,
    get_db_session,
)
from .utils import (
    normalize_text,
    normalize_options,
    calculate_similarity,
    is_similar_question,
)

__all__ = [
    # Models
    "Question",
    "Answer",
    "QuestionProviderAnswer",
    "Base",
    # Config
    "DatabaseConfig",
    "DatabaseManager",
    "db_manager",
    "init_database",
    "close_database",
    "get_db_session",
    # Utils
    "normalize_text",
    "normalize_options",
    "calculate_similarity",
    "is_similar_question",
]
