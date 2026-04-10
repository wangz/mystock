---
name: refactor
overview: 改造为微信扫码登录多用户系统，SQLite按用户隔离数据，写操作需登录。
design:
  architecture:
    framework: vue
  styleKeywords:
    - 金融科技风 FinTech
    - 微信品牌色集成
    - 专业投资工具
    - 流畅扫码体验
    - 深蓝主色调
    - 翠绿涨跌色
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 20px
      weight: 600
    subheading:
      size: 16px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#07C160"
      - "#1890FF"
      - "#1A56DB"
    background:
      - "#F5F7FA"
      - "#FFFFFF"
      - "#F0F2F5"
      - "#EBEEF5"
    text:
      - "#303133"
      - "#606266"
      - "#909399"
    functional:
      - "#67C23A"
      - "#F56C6C"
      - "#E6A23C"
      - "#409EFF"
todos:
  - id: db-init
    content: 创建后端数据库初始化模块 (db_init.py, models.py, config.py) 和用户服务层 (user_service.py)，包含 users/user_data 表结构定义、数据迁移脚本、以及按 user_id 隔离的数据读写方法
    status: in_progress
  - id: auth-module
    content: 创建微信 OAuth2.0 认证模块 (auth.py)，实现：生成扫码 URL 接口、微信回调处理、JWT 签发与校验中间件、token 自动刷新机制
    status: pending
    dependencies:
      - db-init
  - id: backend-refactor
    content: 改造后端 main.py：接入 auth 中间件、替换所有 load_data()/save_data()/load_memos() 调用为 user_service 方法、添加微信登录/回调/用户信息 API 路由、更新 .env.example 配置模板
    status: pending
    dependencies:
      - auth-module
  - id: frontend-login-ui
    content: 改造前端 index.html：Header 区域添加登录/用户信息 UI、新建微信扫码 LoginDialog 弹窗组件、编写 auth 状态管理逻辑 (login/logout/checkAuth)、实现 API 请求拦截器自动附加 JWT Token
    status: pending
    dependencies:
      - backend-refactor
  - id: frontend-auth-gate
    content: 在前端实现权限门控：添加股票/删除股票/保存备忘/记录感悟/排序等写操作前的登录检查、未登录自动弹出登录框、已登录感悟备忘区的正常启用
    status: pending
    dependencies:
      - frontend-login-ui
  - id: migration-test
    content: 端到端测试与调试：验证完整登录流程（扫码->回调->JWT签发->前端存储->后续请求带Token）、数据隔离（不同用户看到各自数据）、未登录时的权限限制、旧数据自动迁移、以及公开 API 的可用性
    status: pending
    dependencies:
      - frontend-auth-gate
---

## 产品概述

将 ai-stock 个人股票管理工具改造为支持**邮箱+密码注册登录**的多用户系统。每个注册用户拥有独立的持仓、观察仓、备忘、感悟数据，数据在 SQLite 中按 user_id 隔离存储。未登录用户可浏览行情和公开分析功能（打板、股东动态、双五、R15等），但无法进行写操作（添加/删除股票、备忘、感悟）。

## 核心功能

- **邮箱密码注册/登录**: 用户通过邮箱注册账号，使用邮箱+密码登录，后端用 bcrypt 加密存储密码，JWT Token 维持会话
- **多用户数据隔离**: 在现有 SQLite (finance_data.db) 中新增 `users` 表和 `user_data` 表，所有个人业务数据按 user_id 隔离
- **权限控制**: 写操作 API 需要 Authorization header 携带有效 JWT Token；读操作 API 返回当前用户数据；公共分析 API 无需认证
- **前端登录态管理**: 登录/注册弹窗组件（Tab切换）、Token 持久化（localStorage，7天有效）、API 请求自动携带 Token
- **数据迁移**: 将现有的 portfolio_data.json 和 memos.json 数据迁移到 SQLite 新表中，分配给默认用户或首个注册用户

### 视觉效果

- 页面 header 右侧新增"登录/头像+昵称"按钮区域
- 未登录时：显示蓝色"登录 / 注册"按钮；点击弹出居中登录对话框
- 已登录时：显示圆形头像图标 + 昵称；点击可下拉退出登录
- 登录弹窗：el-dialog + el-radio-group 切换"登录/注册"两个Tab，表单风格统一精致
- 未登录用户尝试执行添加股票/保存备忘/记录感悟等操作时，自动触发登录弹窗提示

## Tech Stack

- **后端**: Python FastAPI (已有) + PyJWT (JWT签发校验) + bcrypt (密码加密)
- **前端**: Vue 3 + Element Plus (已有)
- **数据库**: SQLite (已有 finance_data.db 扩展)
- **认证协议**: 邮箱密码 + JWT (JSON Web Token)

## 实现策略

整体采用**分层架构**改造：

1. 后端新增 `config.py` 配置模块（JWT密钥等）
2. 后端新增 `db_init.py` 数据库初始化（users/user_data 表结构 + 数据迁移）
3. 后端新增 `auth.py` 认证模块（注册/登录/JWT签发校验/依赖注入中间件）
4. 后端新增 `user_service.py` 用户服务层（替代 load_data/save_data/load_memos）
5. 后端改造 `main.py` 接入认证中间件 + 新增 auth 路由
6. 前端改造 Header 区域 + 登录弹窗 + API拦截器 + 权限门控

**关键决策**:

- **JWT 存储**: 前端 localStorage，过期时间 7 天
- **密码加密**: 使用 bcrypt（加盐哈希），不可逆
- **数据库设计**: users 表存用户基础信息(email/password_hash/nickname/avatar)，user_data 表按 (user_id, data_type, data_key) 存储各类 JSON 数据
- **向后兼容**: 保留原 portfolio_data.json 和 memos.json 作为迁移源，启动时检测旧数据并自动迁移到默认用户
- **无需第三方审核**: 邮箱方案不依赖任何外部平台审核，立即可开发调试

### 性能与可靠性考虑

- JWT 校验使用本地算法（无需网络请求），性能影响极小
- bcrypt 哈希仅发生在注册/登录瞬间，不影响日常接口性能
- SQLite user_data 表建立 (user_id, data_type, data_key) 复合索引保证查询效率
- 公开 API（行情/分析类）保持无认证访问，不受影响

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3 + Element Plus)              │
│                                                             │
│  ┌──────────┐   ┌──────────────────┐   ┌────────────────┐    │
│  │ Header   │   │  Main Content     │   │ Login Dialog    │    │
│  │ 登录按钮  │   │  持仓 | 观察 | 分析 │   │  邮箱密码表单   │    │
│  └──────────┘   └──────────────────┘   └────────────────┘    │
│         │                  │                      │           │
│         │          ┌─────┴─────┐               │           │
│         │          │ API Interceptor             │           │
│         │          │ (自动附加Token)            │           │
│         └──────────┼────────────┘               └───┬───────┘   │
├─────────────────────┼─────────────────────────────────┼───────────┤
│                     ▼                                 ▼           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Backend                          │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │Auth中间件 │→ │ Public APIs  │  │ Auth APIs (需JWT)   │   │  │
│  │  │(JWT Dep) │  │ /api/*analysis│ │ /api/portfolio     │   │  │
│  │  └──────────┘  │ /api/stocks  │ │ /api/watchlist     │   │  │
│  │                │ /api/search  │ │ /api/insights      │   │  │
│  │                │ ...          │ /api/stock-memo     │   │  │
│  │                └─────────────┘ │ /api/add-stock      │   │  │
│  │                                   └─────────────────────┘   │  │
│  │  ┌──────────────┐  ┌─────────────────────────────┐    │  │
│  │  │ Auth Module   │  │ User Service Layer          │    │  │
│  │  │(register/    │  │ - get_user_portfolio(uid)    │    │  │
│  │  │ login/JWT)   │  │ - get_user_watchlist(uid)    │    │  │
│  │  │              │  │ - get_user_memos(uid)       │    │  │
│  │  └──────────────┘  │ - get_user_insights(uid)    │    │  │
│  │                    │ - get_user_history(uid)      │    │  │
│  │                    └─────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────┼──────────────────────────────┐   │
│  │                 finance_data.db (SQLite)               │   │
│  │  ┌──────────┐  ┌──────────────────┬─────────────┐  │   │
│  │  │ stock_codes│  │ users            │ user_data   │  │   │
│  │  │ roe_data  │  │ (user_id,email,  │(uid,type,   │  │   │
│  │  │ dividend_ │  │  password_hash,  │ key,json_val)│  │   │
│  │  │ cache     │  │  nickname,avatar)│ type:        │  │   │
│  │  │ roe_summary│  │                  │ portfolio/   │  │   │
│  │  └──────────┘  │                  │ watchlist/   │  │   │
│  │                  │                  │ insights/    │  │   │
│  │                  │                  │ memos/      │  │   │
│  │                  │                  │ history)    │  │   │
│  │                  └──────────────────┴─────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 目录结构

```
/Users/wz/Documents/trae_projects/ai-stock/
├── backend/
│   ├── main.py                    # [MODIFY] 添加 auth 路由、修改现有API接入用户体系
│   ├── config.py                   # [NEW] 配置管理：JWT_SECRET等
│   ├── auth.py                     # [NEW] 认证模块：注册/登录/JWT签发校验/依赖注入
│   ├── user_service.py             # [NEW] 用户数据服务层：替代load_data/save_data/load_memos
│   ├── db_init.py                 # [NEW] 数据库初始化：创建表、索引、旧数据迁移
│   ├── models.py                  # [NEW] Pydantic模型：User, UserData, RegisterRequest等
│   └── requirements.txt            # [MODIFY] 添加 pyjwt, bcrypt 依赖
├── frontend/
│   └── index.html                 # [MODIFY]
│       # - CSS: 新增登录弹窗样式、用户头像样式
│       # - HTML: Header区域添加登录按钮/用户信息区、LoginDialog弹窗
│       # - JS: auth状态管理(login/logout/checkAuth)、API请求拦截器(authFetch+requireLogin)、权限门控
├── finance_data.db               # [MODIFY] 启动时自动新增 users 和 user_data 表
├── portfolio_data.json            # [保留] 启动时自动迁移到SQLite
└── memos.json                   # [保留] 启动时自动迁移到SQLite
```

## 关键代码结构

```python
# models.py - 核心数据模型
class User(BaseModel):
    user_id: str        # UUID主键
    email: str          # 邮箱（唯一）
    nickname: str
    avatar_url: Optional[str]

class RegisterRequest(BaseModel):
    email: str
    password: str       # 明文（后端bcrypt加密）
    nickname: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

# user_data 表的数据类型枚举
class DataType(str, Enum):
    PORTFOLIO = "portfolio"
    WATCHLIST = "watchlist"
    INSIGHTS = "insights"
    MEMOS = "memos"
    HISTORY = "history"

# auth.py - 核心函数签名
def hash_password(password: str) -> str ...           # bcrypt加密
def verify_password(plain: str, hashed: str) -> bool ...  # 密码验证
def create_access_token(user_id: str, email: str) -> str ...  # JWT签发
def decode_token(token: str) -> dict ...               # JWT解码校验
async def get_current_user(authorization: Optional[str]) -> dict ...  # FastAPI依赖注入
```

## Auth API 接口设计

| 接口 | 方法 | 说明 | 认证 |
| --- | --- | --- | --- |
| `/api/auth/register` | POST | 注册（邮箱+密码+可选昵称） | 不需要 |
| `/api/auth/login` | POST | 登录（返回token+user信息） | 不需要 |
| `/api/auth/userinfo` | GET | 获取当前登录用户信息 | 需要 |
| `/api/auth/change-password` | POST | 修改密码 | 需要 |


## 数据库表结构

```sql
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- 用户数据表（按类型隔离存储各类JSON数据）
CREATE TABLE IF NOT EXISTS user_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    data_key TEXT DEFAULT '',
    json_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, data_type, data_key)
);
CREATE INDEX idx_user_data_lookup ON user_data(user_id, data_type);
```

**data_type 说明**：

- `portfolio`: 持仓列表，一个用户一条记录，json_value 为数组 `["sh600519", "sz000858"]`
- `watchlist`: 观察列表，同上
- `insights`: 感悟列表，一个用户一条记录，json_value 为对象数组
- `memos`: 备忘，每只股票一条记录，data_key 为股票代码
- `history`: 删除历史，一个用户一条记录，json_value 为对象数组

## 设计风格

采用现代金融科技风格（FinTech），以深蓝(#1A56DB)为主色调，搭配翠绿(#07C160)作为操作确认色。登录弹窗使用卡片式设计，表单简洁清晰，符合 Element Plus 设计规范。

## 页面规划

### Page 1: 主界面（修改现有页面）

#### Block 1: Header 导航栏（修改）

- 左侧保持原有控制区（自动刷新开关、手动刷新、时间标签）
- 中间保持统计行（持仓数量、观察数量）
- **右侧改造为登录/用户区域**:
- **未登录状态**: 显示蓝色圆角按钮 "登录 / 注册"，hover 时微发光效
- **已登录状态**: 显示圆形头像（30px，无头像则显示昵称首字）+ 昵称文本；hover 显示 el-dropdown 菜单含 "退出登录"

#### Block 2: 登录/注册弹窗（新增 Dialog 组件）

- 居中模态对话框，宽度约 420px，圆角阴影卡片
- **顶部 Tab 切换**: el-radio-group 包含 "登录" 和 "注册" 两个 tab 按钮
- **登录表单**:
- 邮箱输入框（el-input type=email，prefix-icon=Message）
- 密码输入框（el-input type=password，show-password，prefix-icon=Lock）
- 蓝色"登录"按钮（width=100%，loading 状态）
- 底部文字："还没有账户？立即注册"
- **注册表单**:
- 邮箱输入框（placeholder="用于登录和找回密码"）
- 昵称输入框（可选，placeholder="显示名称"）
- 密码输入框（placeholder="至少6位字符"）
- 确认密码输入框（placeholder="再次输入密码"）
- 绿色"注册"按钮（width=100%，loading 状态）
- 底部文字："已有账户？返回登录"

#### Block 3: 持仓/观察面板（保持不变，但数据来源改为用户级）

- "➕ 添加" 按钮：未登录点击 → 触发登录弹窗
- 删除操作(x按钮)：未登录点击 → 触发登录弹窗
- 浏览功能不受影响

#### Block 4: 分析区 - 我又悟了 Tab

- 未登录：输入框禁用，placeholder="登录后即可记录感悟..."
- 已登录：正常可用，可增删感悟

#### Block 5: 分析区 - 我的备忘 Tab

- 与感悟类似的权限控制逻辑

#### Block 6: 对话区（AI对话）

- 登录后 AI 对话能引用用户的持仓/观察列表上下文
- 未登录时可使用但无个性化上下文

## 权限划分清单

### 需要JWT认证的写操作API（10个）:

1. `POST/DELETE /api/portfolio/{ticker}` - 添加/移除持仓
2. `POST/DELETE /api/watchlist/{ticker}` - 添加/移除观察仓
3. `POST /api/insights` - 添加感悟
4. `GET /api/insights` - 获取感悟（用户自己的）
5. `DELETE /api/insights/{index}` - 删除感悟
6. `POST /api/stock-memo` - 保存备忘
7. `GET /api/stock-memo` - 获取备忘（用户自己的）
8. `POST /api/add-stock` - 添加股票
9. `POST /api/stock-order/{list_name}` - 保存排序
10. `POST /api/stock-history` - 添加历史记录
11. `GET /api/stock-history` - 获取历史（用户自己的）
12. `POST /api/stock-restore` - 恢复股票
13. `DELETE /api/stock-history/{index}` - 删除历史
14. `POST /api/chat` - 对话（需用户上下文）

### 公开的读操作API（无需认证，9个）:

1. `GET /api/limit-up-analysis` - 打板分析
2. `GET /api/shareholder-activity` - 股东动态
3. `GET /api/double-five-stocks` - 双五股票
4. `GET /api/r15-stocks` - R15股票
5. `GET /api/search-stock` - 搜索股票
6. `GET /api/all-stock-codes` - 所有股票代码
7. `GET /api/roe-data/{code}` - ROE数据
8. `GET /api/stock-detail/{code}` - 股票详情
9. `GET /api/stock-dividend/{code}` - 分红数据
10. `GET /api/data` - 全量数据（公开版，不含用户私人数据）
11. `GET /api/stock-list` - 股票列表（公开版）

### 需要JWT认证的读操作API（返回当前用户数据）:

1. `GET /api/portfolio` - 持仓（带实时价格，用户自己的）
2. `GET /api/watchlist` - 观察仓（带实时价格，用户自己的）

## SubAgent

- **code-explorer**
- Purpose: 在实现过程中深度探索 main.py 的具体函数位置、调用关系和数据流，确保改造不遗漏任何 API 端点
- Expected outcome: 精确定位所有需要修改的函数和路由，确保改造方案的准确性