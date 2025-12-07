"""
数据库配置和连接管理

提供PostgreSQL数据库的连接配置和会话管理。
使用异步SQLAlchemy支持高并发场景。
"""

import os
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from asyncpg import exceptions as pg_exc
from dotenv import load_dotenv

from .models import Base
from logger import get_logger

log = get_logger("database")

load_dotenv()  # 加载 .env 文件


class DatabaseConfig:
    """
    数据库配置类

    从环境变量读取数据库连接信息，提供默认值。
    支持通过环境变量配置：
    - DB_HOST: 数据库主机地址
    - DB_PORT: 数据库端口
    - DB_USER: 数据库用户名
    - DB_PASSWORD: 数据库密码
    - DB_NAME: 数据库名称
    """

    def __init__(self):
        # 从环境变量读取配置，提供默认值
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        self.database = os.getenv("DB_NAME", "tikuadapter")

        # 连接池配置
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))

        # 是否启用SQL日志（开发环境可以开启）
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"

    def get_database_url(self) -> str:
        """
        构造异步PostgreSQL连接URL

        Returns:
            异步数据库连接字符串

        Example:
            postgresql+asyncpg://user:password@localhost:5432/tikuadapter
        """
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseInitError(Exception):
    """数据库初始化失败异常，包含用户友好的错误信息"""
    pass


class DatabaseManager:
    """
    数据库管理器

    负责数据库引擎和会话的创建、管理和销毁。
    使用单例模式确保全局只有一个数据库连接池。
    """

    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置（只在第一次创建时执行）"""
        if not hasattr(self, '_initialized'):
            self.config = DatabaseConfig()
            self._initialized = True

    def _translate_error(self, error: Exception) -> str:
        """将数据库异常转换为用户友好的中文提示"""
        orig = getattr(error, "orig", error)
        msg = str(orig).lower()
        cfg = self.config

        if isinstance(orig, pg_exc.InsufficientPrivilegeError) or "permission denied" in msg:
            return (
                f"数据库权限不足：用户 `{cfg.user}` 没有在 schema 中创建表的权限。\n"
                f"解决方法：请让数据库管理员执行 GRANT CREATE ON SCHEMA public TO {cfg.user};"
            )

        if isinstance(orig, (pg_exc.InvalidPasswordError, pg_exc.InvalidAuthorizationSpecificationError)) or "authentication failed" in msg:
            return (
                f"数据库认证失败：用户名或密码错误。\n"
                f"请检查环境变量 DB_USER={cfg.user} 和 DB_PASSWORD 是否正确。"
            )

        if isinstance(orig, pg_exc.InvalidCatalogNameError) or (f'database "{cfg.database}"' in msg and "does not exist" in msg):
            return (
                f"数据库不存在：`{cfg.database}` 不存在。\n"
                f"请先创建数据库或修改 DB_NAME 环境变量。"
            )

        is_conn_refused = (
            isinstance(orig, ConnectionRefusedError)
            or (isinstance(orig, OSError) and getattr(orig, "errno", None) in {61, 111})
            or "connection refused" in msg
        )
        if is_conn_refused:
            return (
                f"无法连接数据库：{cfg.host}:{cfg.port} 连接被拒绝。\n"
                f"请确认 PostgreSQL 服务已启动且网络可达。"
            )

        if "timeout" in msg:
            return (
                f"数据库连接超时：无法在规定时间内连接到 {cfg.host}:{cfg.port}。\n"
                f"请检查网络连接和防火墙设置。"
            )

        return (
            f"数据库初始化失败：发生未知错误。\n"
            f"请检查数据库配置（{cfg.host}:{cfg.port}/{cfg.database}）并查看日志获取详细信息。"
        )

    async def init_engine(self):
        """
        初始化数据库引擎

        创建异步数据库引擎和会话工厂。
        应该在应用启动时调用一次。
        """
        if self._engine is None:
            # 创建异步引擎
            self._engine = create_async_engine(
                self.config.get_database_url(),
                echo=self.config.echo,  # 是否打印SQL语句
                pool_size=self.config.pool_size,  # 连接池大小
                max_overflow=self.config.max_overflow,  # 最大溢出连接数
                pool_pre_ping=True,  # 连接前检查连接是否有效
                pool_recycle=3600,  # 连接回收时间（秒）
            )

            # 创建会话工厂
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,  # 提交后不过期对象
            )

            log.info(f"数据库引擎已初始化: {self.config.host}:{self.config.port}/{self.config.database}")

    async def create_tables(self):
        """
        创建所有数据库表

        根据models.py中定义的模型创建表结构。
        如果表已存在则跳过。
        应该在应用首次部署或数据库迁移时调用。
        """
        if self._engine is None:
            await self.init_engine()

        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                log.info("数据库表创建完成")
        except SQLAlchemyError as e:
            user_msg = self._translate_error(e)
            log.error(f"数据库表创建失败: {user_msg}", exc_info=True)
            raise DatabaseInitError(user_msg) from e

    async def drop_tables(self):
        """
        删除所有数据库表

        警告：这会删除所有数据！仅用于开发/测试环境。
        """
        if self._engine is None:
            await self.init_engine()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            log.warning("数据库表已删除")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取数据库会话（上下文管理器）

        使用方式：
            async with db_manager.get_session() as session:
                # 执行数据库操作
                result = await session.execute(query)
                await session.commit()

        Yields:
            AsyncSession: 数据库会话对象

        Raises:
            Exception: 数据库操作异常会自动回滚
        """
        if self._session_factory is None:
            await self.init_engine()

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def close(self):
        """
        关闭数据库连接

        应该在应用关闭时调用，释放所有数据库连接。
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            log.info("数据库连接已关闭")


# 全局数据库管理器实例
db_manager = DatabaseManager()


async def init_database():
    """
    初始化数据库

    应该在应用启动时调用。
    包括：初始化引擎、创建表结构。

    Raises:
        DatabaseInitError: 数据库初始化失败时抛出，包含用户友好的错误信息
    """
    try:
        await db_manager.init_engine()
        await db_manager.create_tables()
    except DatabaseInitError:
        raise
    except Exception as e:
        user_msg = db_manager._translate_error(e)
        log.error(f"数据库初始化失败: {user_msg}", exc_info=True)
        raise DatabaseInitError(user_msg) from e


async def close_database():
    """
    关闭数据库连接

    应该在应用关闭时调用。
    """
    await db_manager.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的便捷函数

    可以作为FastAPI的依赖注入使用：
        @app.get("/")
        async def handler(session: AsyncSession = Depends(get_db_session)):
            # 使用session进行数据库操作
            pass

    Yields:
        AsyncSession: 数据库会话对象
    """
    async with db_manager.get_session() as session:
        yield session
