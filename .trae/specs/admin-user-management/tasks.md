# 管理员后台管理 - 用户管理功能任务清单

## 任务列表

### 阶段一：数据库迁移

- [ ] **任务 1.1**：创建数据库迁移脚本
  - 在 `users` 表添加 `is_admin` 字段（Boolean，默认 false）
  - 在 `users` 表添加 `last_login` 字段（DateTime）
  - 创建 `migrations/002_add_admin_fields.py` 迁移脚本
  - 定义向上和向下迁移操作
  - **迁移脚本要求**：
    - 幂等性：可安全重复执行
    - 可回滚：提供 `downgrade()` 函数
    - 版本控制：使用语义化版本号
    - 日志记录：记录执行时间和结果

- [ ] **任务 1.2**：编写迁移执行器
  - 创建 `migrations/run_migration.py` 执行脚本
  - 实现版本检查和状态记录
  - 支持增量迁移（只执行未执行的迁移）
  - 添加迁移日志记录
  - **执行器功能**：
    - `get_current_version()` - 获取当前数据库版本
    - `get_pending_migrations()` - 获取待执行的迁移
    - `run_migrations()` - 执行所有待执行的迁移
    - `rollback(version)` - 回滚到指定版本

- [ ] **任务 1.3**：创建初始管理员账户
  - 插入 `admin@mystock.local` 管理员账户
  - 设置默认密码（环境变量配置）
  - 密码哈希处理（使用 bcrypt）
  - 确保管理员唯一性

- [ ] **任务 1.4**：创建数据验证脚本
  - 验证迁移后数据完整性
  - 验证 `is_admin` 字段正确设置
  - 验证管理员账户存在且可登录
  - 验证现有用户数据不受影响
  - 生成迁移验证报告

- [ ] **任务 1.5**：编写生产环境部署指南
  - 创建 `migrations/MIGRATION_GUIDE.md` 文档
  - 说明如何在生产环境执行迁移
  - 提供回滚步骤和注意事项
  - 添加常见问题解答
  - **部署流程**：
    1. 备份当前数据库
    2. 确认迁移脚本已通过测试
    3. 确认回滚方案已准备好
    4. 通知相关人员维护窗口
    5. 停止应用服务
    6. 执行数据库迁移
    7. 验证迁移结果
    8. 启动应用服务

- [ ] **任务 1.6**：测试数据库迁移
  - 测试迁移脚本执行
  - 测试回滚功能
  - 验证数据完整性
  - 模拟生产环境迁移流程

### 阶段二：后端 API 实现

- [ ] **任务 2.1**：修改认证模块
  - 在 `auth.py` 中添加管理员验证函数
  - 添加 `require_admin` 依赖项
  - 修改 `verify_admin` 函数验证管理员权限

- [ ] **任务 2.2**：添加管理员登录 API
  - 实现 `POST /api/admin/login`
  - 验证管理员凭证
  - 返回管理员 JWT Token

- [ ] **任务 2.3**：实现获取用户列表 API
  - 实现 `GET /api/admin/users`
  - 支持分页参数（page, page_size）
  - 支持搜索参数（search）
  - 支持排序参数（sort_by, sort_order）
  - 返回用户列表和统计信息

- [ ] **任务 2.4**：实现获取用户详情 API
  - 实现 `GET /api/admin/users/{user_id}`
  - 返回用户完整信息
  - 包含持仓、观察列表等详情

- [ ] **任务 2.5**：实现获取统计信息 API
  - 实现 `GET /api/admin/stats`
  - 统计总用户数、今日活跃数、本月新增数
  - 统计总持仓数、总观察列表数

### 阶段三：前端 UI 实现

- [ ] **任务 3.1**：创建管理员登录页面
  - 创建 `/admin-login` 路由
  - 邮箱和密码输入框
  - 登录按钮和错误提示

- [ ] **任务 3.2**：创建管理主页面框架
  - 创建 `/admin` 路由
  - 侧边栏菜单
  - 顶部导航栏

- [ ] **任务 3.3**：实现统计信息面板
  - 显示 4 个统计卡片
  - 总用户数、今日活跃、本月新增、总持仓数
  - 数字醒目展示

- [ ] **任务 3.4**：实现用户列表组件
  - 表格展示用户列表
  - 列：邮箱、用户名、注册时间、最后登录、操作
  - 分页组件

- [ ] **任务 3.5**：实现用户搜索功能
  - 搜索框组件
  - 支持按邮箱、昵称搜索
  - 实时搜索或按钮触发

- [ ] **任务 3.6**：实现用户详情弹窗
  - 点击"查看"按钮打开弹窗
  - 显示用户基本信息
  - 显示用户持仓列表
  - 显示用户观察列表

- [ ] **任务 3.7**：实现权限控制
  - 未登录用户访问管理页面 → 重定向到登录页
  - 非管理员用户访问 → 显示权限不足提示

### 阶段四：测试

- [ ] **任务 4.1**：API 测试
  - 测试管理员登录 API
  - 测试用户列表 API（正常、分页、搜索、排序）
  - 测试用户详情 API
  - 测试统计信息 API
  - 测试权限验证（普通用户访问应被拒绝）

- [ ] **任务 4.2**：前端测试
  - 测试管理员登录流程
  - 测试用户列表展示
  - 测试搜索和筛选
  - 测试分页功能
  - 测试用户详情弹窗
  - 测试权限控制

- [ ] **任务 4.3**：集成测试
  - 完整的管理员操作流程
  - 前后端联调测试
  - 异常情况处理

---

## 任务依赖关系

```
任务 1.1 ─> 任务 1.2 ─> 任务 1.3 ─> 任务 1.4 ─> 任务 1.5 ─> 任务 1.6
                      │
                      └──> 任务 2.1 ─> 任务 2.2 ─> 任务 2.3 ─> 任务 2.4 ─> 任务 2.5
                                                                            │
任务 3.1 ─> 任务 3.2 ─> 任务 3.3 ─> 任务 3.4 ─> 任务 3.5 ─> 任务 3.6 ─> 任务 3.7
                                                                            │
任务 1.6 + 任务 2.5 + 任务 3.7 ──> 任务 4.1 ─> 任务 4.2 ─> 任务 4.3
```

**关键依赖**：
- 任务 1.1-1.6（数据库迁移）必须在后端 API 实现前完成
- 任务 1.3（创建管理员账户）必须在测试前完成
- 任务 2.1-2.5（后端 API）必须在任务 3.1-3.7（前端 UI）前完成
- 任务 1.6 + 2.5 + 3.7 完成后才能进行测试

**关键路径**：
- 数据库迁移 → 后端 API → 任务 4.1-4.3
- 数据库迁移 → 后端 API → 前端 UI → 任务 4.2-4.3

---

## 技术实现提示

### 数据库迁移实现

#### 1. 迁移脚本结构

```python
# migrations/002_add_admin_fields.py
VERSION = '002'
DESCRIPTION = '添加管理员字段和用户统计字段'

def upgrade(db_path):
    """向上迁移：添加管理员相关字段"""
    import sqlite3
    import bcrypt
    from datetime import datetime
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 检查字段是否已存在（幂等性）
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 2. 添加 is_admin 字段
        if 'is_admin' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
        
        # 3. 添加 last_login 字段
        if 'last_login' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN last_login TEXT')
        
        # 4. 创建迁移记录表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                version TEXT PRIMARY KEY,
                description TEXT,
                applied_at TEXT
            )
        ''')
        
        # 5. 记录迁移（防止重复执行）
        cursor.execute(
            'INSERT OR REPLACE INTO migrations VALUES (?, ?, ?)',
            (VERSION, DESCRIPTION, datetime.now().isoformat())
        )
        
        conn.commit()
        print(f"✅ Migration {VERSION} applied successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration {VERSION} failed: {e}")
        raise
    finally:
        conn.close()

def downgrade(db_path):
    """向下迁移：移除管理员数据（保留字段）"""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 删除管理员账户
        cursor.execute("DELETE FROM users WHERE email = 'admin@mystock.local'")
        
        # 2. 重置所有用户的 is_admin 字段
        cursor.execute('UPDATE users SET is_admin = 0 WHERE is_admin = 1')
        
        # 3. 删除迁移记录
        cursor.execute('DELETE FROM migrations WHERE version = ?', (VERSION,))
        
        conn.commit()
        print(f"✅ Rollback {VERSION} completed")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Rollback {VERSION} failed: {e}")
        raise
    finally:
        conn.close()
```

#### 2. 迁移执行器

```python
# migrations/run_migration.py
import os
import sqlite3
from datetime import datetime

class MigrationRunner:
    def __init__(self, db_path):
        self.db_path = db_path
        self.migrations_dir = 'migrations'
    
    def get_current_version(self):
        """获取当前数据库版本"""
        if not os.path.exists(self.db_path):
            return '000'
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='migrations'
            ''')
            if not cursor.fetchone():
                return '000'
            
            cursor.execute('SELECT version FROM migrations ORDER BY version DESC LIMIT 1')
            result = cursor.fetchone()
            return result[0] if result else '000'
        finally:
            conn.close()
    
    def get_pending_migrations(self):
        """获取待执行的迁移"""
        current = self.get_current_version()
        migrations = []
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.py') and filename.startswith('00'):
                version = filename.split('_')[0]
                if version > current:
                    migrations.append((version, filename))
        
        return migrations
    
    def run_migrations(self):
        """执行所有待执行的迁移"""
        pending = self.get_pending_migrations()
        
        if not pending:
            print("✅ No pending migrations")
            return
        
        for version, filename in pending:
            print(f"\n🔄 Running migration {version}...")
            module_name = filename[:-3]
            module = __import__(f'migrations.{module_name}', fromlist=['upgrade'])
            module.upgrade(self.db_path)
            print(f"✅ Migration {version} completed")
    
    def rollback(self, target_version):
        """回滚到指定版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT version FROM migrations ORDER BY version DESC')
            applied = [row[0] for row in cursor.fetchall()]
            
            for version in applied:
                if version <= target_version:
                    break
                
                print(f"\n🔄 Rolling back migration {version}...")
                module_name = f'{version}_add_admin_fields'
                try:
                    module = __import__(f'migrations.{module_name}', fromlist=['downgrade'])
                    module.downgrade(self.db_path)
                    print(f"✅ Rollback {version} completed")
                except:
                    print(f"⚠️  Migration {version} has no downgrade")
                    cursor.execute('DELETE FROM migrations WHERE version = ?', (version,))
                    conn.commit()
        finally:
            conn.close()

if __name__ == '__main__':
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'user.db'
    
    runner = MigrationRunner(db_path)
    
    if len(sys.argv) > 2 and sys.argv[2] == 'rollback':
        target = sys.argv[3] if len(sys.argv) > 3 else '000'
        runner.rollback(target)
    else:
        runner.run_migrations()
```

#### 3. 管理员账户创建

```python
def create_admin_user(db_path, email, password):
    """创建管理员账户"""
    import bcrypt
    import uuid
    from datetime import datetime
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            print(f"⚠️  Admin user {email} already exists")
            return
        
        # 创建管理员
        cursor.execute('''
            INSERT INTO users (user_id, email, password_hash, nickname, is_admin, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (f'admin_{uuid.uuid4().hex[:8]}', email, password_hash.decode('utf-8'), 
              'Administrator', datetime.now().isoformat()))
        
        conn.commit()
        print(f"✅ Admin user {email} created successfully")
        
    finally:
        conn.close()
```

#### 4. 数据验证脚本

```python
# migrations/validate_migration.py
def validate_migration(db_path):
    """验证迁移后的数据完整性"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    results = {'success': 0, 'warnings': 0, 'errors': 0, 'details': []}
    
    try:
        # 1. 验证字段存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_admin' in columns:
            results['success'] += 1
            results['details'].append('✅ is_admin field exists')
        else:
            results['errors'] += 1
            results['details'].append('❌ is_admin field missing')
        
        if 'last_login' in columns:
            results['success'] += 1
            results['details'].append('✅ last_login field exists')
        else:
            results['errors'] += 1
            results['details'].append('❌ last_login field missing')
        
        # 2. 验证管理员账户
        cursor.execute("SELECT * FROM users WHERE is_admin = 1")
        admin = cursor.fetchone()
        
        if admin:
            results['success'] += 1
            results['details'].append(f'✅ Admin user exists: {admin[1]}')
        else:
            results['warnings'] += 1
            results['details'].append('⚠️  No admin user found')
        
        # 3. 验证迁移记录
        cursor.execute('SELECT * FROM migrations ORDER BY version')
        migrations = cursor.fetchall()
        
        if migrations:
            results['success'] += 1
            results['details'].append(f'✅ {len(migrations)} migration(s) recorded')
        else:
            results['warnings'] += 1
            results['details'].append('⚠️  No migration records')
        
        # 4. 验证现有数据
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        results['details'].append(f'📊 Total users: {total_users}')
        
    finally:
        conn.close()
    
    return results
```

### 后端实现

1. **管理员验证依赖**：

```python
async def require_admin(current_user: dict = Depends(get_current_user)):
    """验证用户是否为管理员"""
    if not current_user.get('is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
```

2. **用户列表查询优化**：

```python
def get_users_with_stats(db_path, page=1, page_size=20, search=None):
    """获取用户列表及其统计数据"""
    conn = sqlite3.connect(db_path)
    # 使用 JOIN 查询获取用户数据和统计
    # 支持分页、搜索、排序
    conn.close()
```

3. **统计信息查询**：

```python
def get_user_stats(db_path):
    """获取用户统计信息"""
    # 总用户数
    # 今日活跃用户数
    # 本月新增用户数
    # 总持仓数
    # 总观察列表数
```

### 前端实现

1. **路由守卫**：

```javascript
// 检查是否为管理员
const isAdmin = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  return user.is_admin === true;
};

// 路由守卫
router.beforeEach((to, from, next) => {
  if (to.path.startsWith('/admin')) {
    if (!isAdmin()) {
      next('/admin-login');
    }
  }
  next();
});
```

2. **状态管理**：

```javascript
// 管理员状态
const adminUsers = ref([]);
const adminStats = ref({});
const adminPagination = ref({ page: 1, pageSize: 20 });
const adminSearch = ref('');
```

3. **API 调用**：

```javascript
// 获取用户列表
const fetchUsers = async () => {
  const response = await fetch(`${API_BASE}/api/admin/users`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

---

## 数据库迁移详细说明

### 迁移脚本结构

```python
# migrations/002_add_admin_fields.py
VERSION = '002'
DESCRIPTION = '添加管理员字段和用户统计字段'

def upgrade(db_path):
    """向上迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 添加 is_admin 字段
    cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    
    # 添加 last_login 字段
    cursor.execute('ALTER TABLE users ADD COLUMN last_login TEXT')
    
    # 创建管理员账户
    # ... 密码哈希处理 ...
    
    # 记录迁移
    cursor.execute('INSERT INTO migrations VALUES (?, ?, ?)',
                   (VERSION, DESCRIPTION, datetime.now()))
    
    conn.commit()
    conn.close()

def downgrade(db_path):
    """向下迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 删除管理员账户
    cursor.execute("DELETE FROM users WHERE email = 'admin@mystock.local'")
    
    # 注意：SQLite 不支持 DROP COLUMN
    # 字段保留，标记为已废弃
    
    # 删除迁移记录
    cursor.execute('DELETE FROM migrations WHERE version = ?', (VERSION,))
    
    conn.commit()
    conn.close()
```
