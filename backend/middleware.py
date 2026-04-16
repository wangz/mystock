"""
请求追踪中间件 - 记录请求来源、用户信息等
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
import logging
import jwt

from config import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseHTTPMiddleware):
    """提取认证用户信息到请求状态"""
    
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                request.state.user_id = payload.get("user_id", "unknown")
            except:
                request.state.user_id = "invalid_token"
        else:
            request.state.user_id = "anonymous"
        
        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求追踪 ID 中间件"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录完整请求来源"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        user_agent = request.headers.get("user-agent", "unknown")[:100]
        referer = request.headers.get("referer", "-")
        auth_user = getattr(request.state, "user_id", "anonymous")
        
        log_base = (
            f"[{request_id}] {request.method} {request.url.path} | "
            f"IP: {client_ip} | UA: {user_agent}"
        )
        
        logger.info(f"{log_base} | 开始")
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            logger.info(
                f"{log_base} | "
                f"状态码: {response.status_code} | "
                f"用户: {auth_user} | "
                f"耗时: {duration:.3f}s | "
                f"Referer: {referer}"
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{log_base} | "
                f"用户: {auth_user} | "
                f"错误: {str(e)} | "
                f"耗时: {duration:.3f}s",
                exc_info=True
            )
            raise
