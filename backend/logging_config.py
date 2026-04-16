"""
日志配置文件 - 统一管理应用日志
"""

import logging
import logging.handlers
import os
import re
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""
    
    SENSITIVE_PATTERNS = [
        (r'(password["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(token["\']?\s*[:=]\s*)["\']([^"\']{20,})["\']', r'\1******'),
        (r'(jwt["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(secret["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(authorization["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
    ]
    
    def filter(self, record):
        message = record.msg
        
        if isinstance(message, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
            
            if record.args:
                record.args = tuple(
                    re.sub(pattern, replacement, str(arg), flags=re.IGNORECASE)
                    if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        record.msg = message
        return True


def setup_logging():
    """配置全局日志"""
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    logger.handlers.clear()
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(file_handler)
    
    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    error_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(error_handler)
    
    return logger


logger = setup_logging()
