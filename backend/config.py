"""
配置文件 - JWT 认证配置
"""

import secrets
import os
import json

# 数据库配置
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "finance_data.db")

# JWT 配置 - 确保持久化
SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jwt_secret")

def _load_jwt_secret():
    """加载或生成持久化的 JWT Secret"""
    if os.environ.get('JWT_SECRET'):
        return os.environ['JWT_SECRET']
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, 'r') as f:
            return f.read().strip()
    # 生成新的 secret 并保存
    secret = secrets.token_urlsafe(32)
    with open(SECRET_FILE, 'w') as f:
        f.write(secret)
    return secret

JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = 'HS256'
JWT_EXPIRE_DAYS = 7

# 默认用户 ID（用于兼容旧数据）
DEFAULT_USER_ID = 'default_user'
