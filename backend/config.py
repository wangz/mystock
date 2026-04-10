"""
配置文件 - JWT 认证配置
"""

import secrets
import os

# 数据库配置
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "finance_data.db")

# JWT 配置
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRE_DAYS = 7

# 默认用户 ID（用于兼容旧数据）
DEFAULT_USER_ID = 'default_user'
