# ==============================================================================
# 日志管理模块 / Logger Management Module
# ==============================================================================
# 提供统一的日志记录功能
# Provides unified logging functionality
# ==============================================================================

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.config import get_config

# 标记是否已初始化 / Flag for initialization status
_initialized = False


def setup_logger(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    console_output: Optional[bool] = None
) -> None:
    """
    设置日志记录器 / Setup logger
    
    配置日志输出目标、格式和级别
    Configure log output destination, format and level
    
    Args:
        log_level: 日志级别 / Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径 / Log file path
        console_output: 是否输出到控制台 / Whether to output to console
    """
    config = get_config()
    
    # 使用参数或配置文件中的值 / Use parameters or values from config file
    level = log_level or config.logging.level
    file_path = log_file or config.logging.file_path
    to_console = console_output if console_output is not None else config.logging.console_output
    
    # 移除默认处理器 / Remove default handlers
    logger.remove()
    
    # Loguru格式 / Loguru format
    loguru_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 添加控制台处理器 / Add console handler
    if to_console:
        logger.add(
            sys.stdout,
            format=loguru_format,
            level=level,
            colorize=True
        )
    
    # 添加文件处理器 / Add file handler
    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            file_path,
            format=loguru_format,
            level=level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8"
        )


def get_logger(name: Optional[str] = None):
    """
    获取日志记录器实例 / Get logger instance
    
    Args:
        name: 日志记录器名称 / Logger name
        
    Returns:
        Logger: 日志记录器 / Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


def init_logging() -> None:
    """
    初始化日志系统 / Initialize logging system
    
    在应用启动时调用此函数，只会初始化一次
    Call this function at application startup, will only initialize once
    """
    global _initialized
    if not _initialized:
        setup_logger()
        logger.info("日志系统初始化完成 / Logging system initialized")
        _initialized = True
