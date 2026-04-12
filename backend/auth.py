"""
认证模块 - JWT 认证、注册、登录
"""

import os
import sqlite3
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DB = os.path.join(BASE_DIR, "user_data.db")

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """bcrypt 加密密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    """创建 JWT Token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """获取当前用户（依赖注入）"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息"
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期"
        )
    
    return payload

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """获取当前用户（可选，不强制）"""
    if credentials is None:
        print(f"[DEBUG] get_optional_user: credentials is None")
        return None
    
    print(f"[DEBUG] get_optional_user: credentials={credentials}")
    token = credentials.credentials
    print(f"[DEBUG] get_optional_user: token={token[:20]}..." if token else "[DEBUG] get_optional_user: token is empty")
    result = decode_token(token)
    print(f"[DEBUG] get_optional_user: decode result={result}")
    return result

def get_user_by_email(email: str) -> Optional[dict]:
    """根据邮箱获取用户"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, email, password_hash, nickname, created_at FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'user_id': row[0],
            'email': row[1],
            'password_hash': row[2],
            'nickname': row[3],
            'created_at': row[4]
        }
    return None

def create_user(email: str, password: str, nickname: str = "") -> dict:
    """创建新用户"""
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, email, password_hash, nickname, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, email, password_hash, nickname, datetime.now(), datetime.now()))
    conn.commit()
    conn.close()
    
    return {
        'user_id': user_id,
        'email': email,
        'nickname': nickname
    }

def update_last_login(user_id: str):
    """更新最后登录时间"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()
