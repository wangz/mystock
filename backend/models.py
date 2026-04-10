"""
Pydantic 数据模型 - 认证相关
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    token: str
    user: dict

class UserInfo(BaseModel):
    user_id: str
    email: str
    nickname: Optional[str] = ""
    created_at: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
