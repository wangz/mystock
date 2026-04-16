# 日志系统增强方案

## 📊 当前日志现状分析

### 🔴 严重问题

#### 1. 核心服务无日志记录
**位置**：`backend/main.py` 和 `backend/auth.py`
**问题**：
- ✅ 已清除所有 print 语句（GOOD）
- ❌ **完全没有任何日志记录**（CRITICAL）
- FastAPI/Uvicorn 只提供基本的请求日志
- 没有应用级别的日志
- 错误发生时无法追踪

**影响**：
- 无法追踪用户行为
- 无法排查生产环境问题
- 无法监控服务健康状态
- 缺少审计日志

**示例**：
```python
# 当前代码（无日志）
@app.post("/api/auth/register")
def register(req: RegisterRequest):
    user = create_user(req.email, req.password)
    return TokenResponse(token=token)

# 理想状态（有日志）
@app.post("/api/auth/register")
def register(req: RegisterRequest):
    logger.info(f"用户注册请求: {req.email}")
    try:
        user = create_user(req.email, req.password)
        logger.info(f"用户注册成功: {user['user_id']}")
        return TokenResponse(token=token)
    except Exception as e:
        logger.error(f"用户注册失败: {req.email}, 错误: {str(e)}")
        raise
```

#### 2. 初始化脚本仍使用 print
**位置**：`backend/db_init.py`, `backend/migrate_watchlist_tags.py`
**问题**：
- ❌ 20+ 处 print 语句未替换为标准日志
- ❌ 无法控制日志级别
- ❌ 无法输出到文件
- ❌ 无法集成到统一日志系统

**示例**：
```python
# 当前代码
print("✅ 数据库表初始化完成")
print(f"  📈 迁移持仓: {len(data['portfolio'])} 条")

# 应该改为
logger.info("数据库表初始化完成")
logger.info(f"迁移持仓: {len(data['portfolio'])} 条")
```

### 🟡 中等问题

#### 3. 缺少日志配置文件
**问题**：
- 没有独立的日志配置文件
- 日志格式不统一
- 日志级别无法动态调整
- 没有日志轮转策略

#### 4. 没有日志文件输出
**问题**：
- 所有日志输出到 stdout
- 日志无法持久化
- 无法进行日志分析
- 容器环境中日志可能丢失

#### 5. 缺少敏感信息过滤
**问题**：
- 密码可能出现在日志中
- JWT token 可能被记录
- 用户隐私数据缺乏保护

### 🟢 轻微问题

#### 6. 缺少请求追踪 ID
**问题**：
- 无法追踪完整请求链路
- 难以定位分布式问题
- 缺少请求关联分析

#### 7. 缺少请求来源记录 ⚠️ 需要补充
**问题**：
- 未记录客户端 IP 地址（无法识别用户来源）
- 未记录 User-Agent（无法识别客户端类型）
- 未记录 Referer（无法追踪来源页面）
- 未记录认证用户信息（无法识别已登录用户）
- 无法进行访问分析和攻击溯源

**影响**：
- 无法分析用户地理分布
- 无法识别爬虫和恶意请求
- 无法追踪用户行为路径
- 难以进行安全审计
- 问题排查时缺少上下文信息

#### 8. 缺少统计指标
**问题**：
- 没有 API 调用统计
- 没有性能指标记录
- 缺少业务指标监控

---

## 🎯 日志增强方案

### 第一阶段：基础日志框架（高优先级）

#### 1.1 创建统一日志配置
**文件**：`backend/logging_config.py`

```python
import logging
import logging.handlers
import os
from pathlib import Path

# 日志目录
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志级别
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def setup_logging():
    """配置全局日志"""
    
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 清除已有的 handlers
    logger.handlers.clear()
    
    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件 Handler（按天轮转）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,  # 保留30天
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger

# 全局 logger
logger = setup_logging()
```

#### 1.2 为 main.py 添加应用日志
**优先级**：高
**位置**：`backend/main.py`

```python
# 在文件顶部添加
import logging
from logging_config import logger

# 在 startup 事件中添加
@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库并迁移数据"""
    logger.info("=" * 50)
    logger.info("MyStock 服务启动中...")
    logger.info("=" * 50)
    
    # 初始化数据库和迁移数据
    init_all()
    logger.info("数据库初始化完成")
    
    # 初始化缓存
    init_cache_table()
    logger.info("缓存表初始化完成")
    
    # 清理过期缓存
    clean_expired_cache()
    logger.info("过期缓存清理完成")
    
    logger.info("✅ MyStock 服务启动成功！")

# 在 shutdown 事件中添加
@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    logger.info("MyStock 服务正在关闭...")

# 在 API 端点中添加日志示例
@app.post("/api/auth/register")
def register(req: RegisterRequest):
    """用户注册"""
    logger.info(f"[注册] 收到注册请求: {req.email}")
    
    if len(req.password) < 6:
        logger.warning(f"[注册] 密码长度不足: {req.email}")
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    
    if get_user_by_email(req.email):
        logger.warning(f"[注册] 邮箱已被注册: {req.email}")
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    try:
        user = create_user(req.email, req.password, req.nickname or "")
        token = create_token(user['user_id'], user['email'])
        logger.info(f"[注册] 用户注册成功: {user['user_id']}")
        return TokenResponse(token=token, user={...})
    except Exception as e:
        logger.error(f"[注册] 用户注册失败: {req.email}, 错误: {str(e)}", exc_info=True)
        raise
```

### 第二阶段：敏感信息保护（中优先级）

#### 2.1 创建日志过滤器
**文件**：`backend/logging_config.py`

```python
import re
import logging

class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""
    
    # 需要过滤的敏感字段
    SENSITIVE_PATTERNS = [
        (r'(password["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(token["\']?\s*[:=]\s*)["\']([^"\']{20,})["\']', r'\1******'),
        (r'(jwt["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(secret["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
        (r'(authorization["\']?\s*[:=]\s*)["\']([^"\']+)["\']', r'\1******'),
    ]
    
    def filter(self, record):
        """过滤敏感信息"""
        message = record.msg
        
        if isinstance(message, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
            
            # 如果是格式化消息，也处理 args
            if record.args:
                record.args = tuple(
                    re.sub(pattern, replacement, str(arg), flags=re.IGNORECASE)
                    if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        record.msg = message
        return True
```

### 第三阶段：请求追踪（可选）

#### 3.1 添加请求 ID 中间件
**文件**：`backend/middleware.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import logging

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求 ID
        request_id = str(uuid.uuid4())[:8]
        
        # 添加到请求状态
        request.state.request_id = request_id
        
        # 添加到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 获取客户端信息
        client_ip = request.client.host if request.client else "unknown"
        
        # 获取 X-Forwarded-For（反向代理场景）
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # 获取 User-Agent
        user_agent = request.headers.get("user-agent", "unknown")[:100]  # 限制长度
        
        # 获取 Referer
        referer = request.headers.get("referer", "-")
        
        # 获取认证用户（如果已登录）
        auth_user = getattr(request.state, "user_id", "anonymous")
        
        # 构建基础日志信息
        log_base = (
            f"[{request_id}] {request.method} {request.url.path} | "
            f"IP: {client_ip} | UA: {user_agent}"
        )
        
        logger.info(f"{log_base} | 开始")
        
        import time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 记录完整请求信息
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
```

#### 3.2 注册中间件
**文件**：`backend/main.py`

```python
from middleware import RequestIDMiddleware, RequestLoggingMiddleware

app = FastAPI(title="MyStock API")

# 注册中间件
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
```

#### 3.3 添加用户认证信息到请求状态
**目的**：在日志中显示已登录用户的 ID

```python
# 在 middleware.py 中添加用户提取中间件
class UserContextMiddleware(BaseHTTPMiddleware):
    """提取认证用户信息到请求状态"""
    
    async def dispatch(self, request: Request, call_next):
        # 尝试从 Authorization header 提取用户信息
        auth_header = request.headers.get("authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                # 解码 JWT token（复用 auth.py 中的逻辑）
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                request.state.user_id = payload.get("user_id", "unknown")
            except:
                request.state.user_id = "invalid_token"
        else:
            request.state.user_id = "anonymous"
        
        return await call_next(request)
```

然后在 main.py 中注册：
```python
app.add_middleware(UserContextMiddleware)  # 放在最前面
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
```

### 第四阶段：脚本日志标准化（低优先级）

#### 4.1 替换 db_init.py 中的 print
**位置**：`backend/db_init.py`

```python
import logging

# 在文件顶部添加
logger = logging.getLogger(__name__)

# 替换所有 print
print("✅ 数据库表初始化完成")
# 改为
logger.info("数据库表初始化完成")

print(f"  📈 迁移持仓: {len(data['portfolio'])} 条")
# 改为
logger.debug(f"迁移持仓: {len(data['portfolio'])} 条")

print(f"  ❌ 迁移失败: {e}")
# 改为
logger.error(f"迁移失败: {e}", exc_info=True)
```

#### 4.2 替换其他脚本
- `backend/migrate_watchlist_tags.py`
- `backend/sync_all_stocks.py`
- `backend/baostock_fetcher.py`

---

## 📋 实施步骤

### 步骤 1：创建日志配置
1. 创建 `backend/logging_config.py`
2. 配置控制台和文件 Handler
3. 配置日志轮转
4. 创建 logs 目录

### 步骤 2：集成到 main.py
1. 导入日志配置
2. 在 startup/shutdown 事件添加日志
3. 选择关键 API 添加请求日志
4. 添加错误日志捕获

### 步骤 3：添加敏感信息过滤
1. 创建 SensitiveDataFilter
2. 注册到日志系统
3. 测试敏感信息过滤

### 步骤 4：添加请求追踪（可选）
1. 创建 middleware.py
2. 实现请求 ID 中间件
3. 实现请求日志中间件
4. 注册到 FastAPI

### 步骤 5：标准化脚本日志
1. 替换 db_init.py 中的 print
2. 替换其他脚本的 print
3. 统一日志格式

---

## 📊 日志使用示例

### 基础日志级别使用

```python
import logging
logger = logging.getLogger(__name__)

# Debug - 开发调试
logger.debug(f"查询参数: {params}")

# Info - 正常流程
logger.info(f"用户 {user_id} 登录成功")

# Warning - 警告但不影响功能
logger.warning(f"用户 {email} 尝试重复注册")

# Error - 错误但可恢复
logger.error(f"数据库连接失败: {e}")

# Critical - 严重错误
logger.critical(f"服务无法启动: {e}")
```

### 结构化日志

```python
# 使用 extra 参数添加额外字段
logger.info(
    "用户操作",
    extra={
        "user_id": user_id,
        "action": "login",
        "ip": client_ip
    }
)

# 输出格式
# 2026-04-15 10:30:45 | INFO     | auth:login:23 | 用户操作 | user_id=123, action=login, ip=192.168.1.1
```

### 异常日志

```python
try:
    result = risky_operation()
except Exception as e:
    # 基本错误日志
    logger.error(f"操作失败: {str(e)}")
    
    # 带堆栈跟踪的错误日志
    logger.error(f"操作失败: {str(e)}", exc_info=True)
    
    # 同时记录上下文
    logger.error(
        f"用户 {user_id} 的操作失败",
        extra={"user_id": user_id, "operation": "buy"},
        exc_info=True
    )
```

### 📝 完整日志输出示例

启用所有增强功能后的日志示例：

```bash
# 应用启动日志
2026-04-15 10:30:45 | INFO     | main:startup_event:190 | ==================================================
2026-04-15 10:30:45 | INFO     | main:startup_event:191 | MyStock 服务启动中...
2026-04-15 10:30:46 | INFO     | main:startup_event:194 | 数据库初始化完成
2026-04-15 10:30:46 | INFO     | main:startup_event:198 | 缓存表初始化完成
2026-04-15 10:30:47 | INFO     | main:startup_event:202 | 过期缓存清理完成
2026-04-15 10:30:47 | INFO     | main:startup_event:204 | ✅ MyStock 服务启动成功！

# 用户注册请求（包含完整来源信息）
2026-04-15 10:31:00 | INFO     | middleware:dispatch:340 | [a1b2c3d4] POST /api/auth/register | IP: 192.168.1.100 | UA: Mozilla/5.0... | 开始
2026-04-15 10:31:00 | INFO     | auth:register:215 | [注册] 收到注册请求: user@example.com
2026-04-15 10:31:00 | INFO     | auth:register:229 | [注册] 用户注册成功: usr_abc123
2026-04-15 10:31:01 | INFO     | middleware:dispatch:360 | [a1b2c3d4] POST /api/auth/register | IP: 192.168.1.100 | UA: Mozilla/5.0... | 状态码: 200 | 用户: usr_abc123 | 耗时: 0.850s | Referer: http://localhost:8000/

# 用户登录请求
2026-04-15 10:32:15 | INFO     | middleware:dispatch:340 | [e5f6g7h8] POST /api/auth/login | IP: 192.168.1.100 | UA: Mozilla/5.0... | 开始
2026-04-15 10:32:16 | INFO     | middleware:dispatch:360 | [e5f6g7h8] POST /api/auth/login | IP: 192.168.1.100 | UA: Mozilla/5.0... | 状态码: 200 | 用户: usr_abc123 | 耗时: 0.120s | Referer: http://localhost:8000/

# 爬虫访问检测
2026-04-15 10:33:00 | INFO     | middleware:dispatch:340 | [i9j0k1l2] GET /api/stock-history | IP: 203.0.113.50 | UA: python-requests/2.28.0 | 开始
2026-04-15 10:33:01 | INFO     | middleware:dispatch:360 | [i9j0k1l2] GET /api/stock-history | IP: 203.0.113.50 | UA: python-requests/2.28.0 | 状态码: 200 | 用户: anonymous | 耗时: 0.950s | Referer: -

# 异常请求日志
2026-04-15 10:34:30 | ERROR    | middleware:dispatch:375 | [m3n4o5p6] POST /api/portfolio | IP: 192.168.1.101 | UA: Mozilla/5.0... | 用户: usr_xyz789 | 错误: Database connection failed | 耗时: 5.230s
Traceback (most recent call last):
  File "app.py", line 150, in dispatch
    response = await call_next(request)
  ...
DatabaseError: Connection timeout

# 反向代理场景（X-Forwarded-For）
2026-04-15 10:35:00 | INFO     | middleware:dispatch:340 | [q7r8s9t0] GET /api/watchlist | IP: 10.0.0.50 | UA: Mozilla/5.0... | 开始
# 日志中记录的 IP 为真实客户端 IP: 203.0.113.100
```

---

## ⚙️ 日志配置选项

### 环境变量控制

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 设置日志文件路径
export LOG_DIR=/var/log/mystock

# 启用敏感信息过滤
export LOG_SENSITIVE_FILTER=true
```

### 日志文件

```
logs/
├── app.log          # 所有日志
├── error.log        # 仅错误日志
├── access.log       # 请求访问日志（可选）
└── audit.log        # 审计日志（可选）
```

---

## 🎯 预期效果

### 完成后可实现

1. ✅ **统一日志格式**
   - 所有日志使用相同格式
   - 包含时间、级别、模块、行号

2. ✅ **持久化存储**
   - 日志保存到文件
   - 自动轮转，保留30天

3. ✅ **分级管理**
   - 可通过环境变量控制日志级别
   - 生产环境减少日志量

4. ✅ **敏感信息保护**
   - 自动过滤密码、token等
   - 防止敏感信息泄露

5. ✅ **请求追踪**
   - 每个请求有唯一 ID
   - 完整追踪请求链路

6. ✅ **问题排查**
   - 错误日志包含堆栈跟踪
   - 上下文信息丰富

---

## ⚠️ 注意事项

1. **不要记录敏感信息**
   - 密码、token、身份证号等
   - 使用过滤器或手动替换

2. **控制日志量**
   - Debug 级别仅在开发环境启用
   - 避免日志文件过大

3. **性能影响**
   - 日志 I/O 有性能开销
   - 生产环境使用异步日志（可选）

4. **磁盘空间**
   - 配置合理的轮转策略
   - 定期清理旧日志

5. **权限管理**
   - logs 目录权限
   - 日志文件访问控制

---

## 📚 参考资源

- [Python Logging 官方文档](https://docs.python.org/3/library/logging.html)
- [FastAPI 日志配置](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [Python Logging CookBook](https://docs.python.org/3/howto/logging-cookbook.html)

---

**创建时间**: 2026-04-15
**预计完成时间**: 
- 第一阶段（基础框架）：30 分钟
- 第二阶段（敏感信息）：20 分钟
- 第三阶段（请求追踪）：30 分钟
- 第四阶段（脚本标准化）：20 分钟
