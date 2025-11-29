"""
日志配置模块

提供统一的日志配置，支持：
1. 控制台输出（带颜色）
2. 文件输出（按天轮转，默认保存到 logs 目录）
3. 通过环境变量配置日志级别
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional


# 日志目录
LOG_DIR = Path(__file__).parent / "logs"


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # 复制 record 避免影响其他 handler
        record = logging.makeLogRecord(record.__dict__)
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "tikuadapter",
    level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    backup_count: Optional[int] = None
) -> logging.Logger:
    """
    配置并返回 logger 实例

    Args:
        name: logger 名称
        level: 日志级别，默认从环境变量 LOG_LEVEL 读取，否则为 INFO
        log_dir: 日志目录，默认为项目下的 logs 目录
        backup_count: 保留的日志文件数量（天数），默认从环境变量 LOG_BACKUP_DAYS 读取，否则为 30 天

    Returns:
        配置好的 logger 实例
    """
    # 从环境变量读取配置
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_dir is None:
        log_dir = LOG_DIR
    if backup_count is None:
        backup_count = int(os.getenv("LOG_BACKUP_DAYS", "30"))

    # 获取或创建 logger
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level, logging.INFO))

    # 日志格式
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(log_format, datefmt=date_format))
    logger.addHandler(console_handler)

    # 文件处理器（按天轮转）
    # 确保日志目录存在
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",      # 每天午夜轮转
        interval=1,           # 间隔 1 天
        backupCount=backup_count,  # 保留天数
        encoding="utf-8"
    )
    # 轮转后的文件名格式：app.log.2024-01-15
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(file_handler)

    # 防止日志向上传播到根 logger
    logger.propagate = False

    return logger


# 创建默认 logger 实例
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    获取子 logger

    Args:
        name: 子 logger 名称，会自动添加前缀

    Returns:
        子 logger 实例

    Example:
        >>> log = get_logger("database")
        >>> log.info("连接成功")  # 输出: tikuadapter.database | INFO | 连接成功
    """
    return logging.getLogger(f"tikuadapter.{name}")
