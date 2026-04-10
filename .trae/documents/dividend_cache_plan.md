# 分红数据缓存优化方案

## 📋 问题分析

### 当前痛点
1. **每次打开详情页都重新获取** - 调用 akshare + baostock，耗时约 3-5 秒
2. **重复查询相同数据** - 同一只股票多次查看时重复请求
3. **分红数据相对稳定** - 年度分红数据不会频繁变化

## 🔍 缓存方案设计

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **内存缓存（lru_cache）** | 简单快速 | 重启后失效 | ⭐⭐ |
| **SQLite 数据库缓存** | 持久化、可查询 | 需管理表结构 | ⭐⭐⭐⭐ |
| **Redis 缓存** | 高性能、支持过期 | 需额外部署 | ⭐⭐⭐ |
| **文件缓存（JSON）** | 简单、易调试 | 并发性能一般 | ⭐⭐⭐ |

### 推荐方案：SQLite 数据库缓存

**理由：**
- 项目已有 SQLite 数据库，无需新增依赖
- 分红数据持久化存储，重启后仍有效
- 支持按股票代码、日期范围查询
- 可设置缓存过期时间

## 📁 实现细节

### 1. 数据库表设计

```sql
CREATE TABLE IF NOT EXISTS dividend_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    dividend_data TEXT NOT NULL,  -- JSON 格式存储分红列表
    cache_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_time TIMESTAMP,
    UNIQUE(stock_code)
);

CREATE INDEX idx_dividend_code ON dividend_cache(stock_code);
CREATE INDEX idx_dividend_expire ON dividend_cache(expire_time);
```

### 2. 缓存策略

```python
# 缓存配置
CACHE_DURATION = 7 * 24 * 60 * 60  # 7 天缓存期

def get_dividend_cached(code: str):
    """
    获取缓存的分红数据
    1. 先查缓存，未过期则返回
    2. 缓存不存在或已过期，则重新获取并更新缓存
    """
    # 查询缓存
    cursor.execute('''
        SELECT dividend_data, expire_time 
        FROM dividend_cache 
        WHERE stock_code = ?
    ''', (code,))
    row = cursor.fetchone()
    
    if row:
        data = json.loads(row[0])
        expire_time = datetime.fromisoformat(row[1])
        
        # 缓存未过期
        if datetime.now() < expire_time:
            return data
    
    # 缓存失效，重新获取
    dividend_list = get_dividend_data(code, years=10)
    
    # 更新缓存
    cursor.execute('''
        INSERT OR REPLACE INTO dividend_cache 
        (stock_code, dividend_data, expire_time)
        VALUES (?, ?, ?)
    ''', (code, json.dumps(dividend_list), 
          datetime.now() + timedelta(seconds=CACHE_DURATION)))
    
    conn.commit()
    return dividend_list
```

### 3. 接口修改

```python
@app.get("/api/stock-dividend/{code}")
def get_stock_dividend(code: str):
    """异步获取股票分红数据（带缓存）"""
    dividend_list = get_dividend_cached(code)
    return {'dividend_list': dividend_list}
```

### 4. 缓存刷新机制

**主动刷新：**
```python
# 手动刷新缓存（管理员功能）
@app.post("/api/cache/refresh/{code}")
def refresh_dividend_cache(code: str):
    # 删除旧缓存
    cursor.execute('DELETE FROM dividend_cache WHERE stock_code = ?', (code,))
    conn.commit()
    
    # 重新获取
    get_dividend_cached(code)
    return {'status': 'success'}
```

**定期清理：**
```python
# 启动时清理过期缓存
def clean_expired_cache():
    cursor.execute('DELETE FROM dividend_cache WHERE expire_time < ?', 
                   (datetime.now(),))
    conn.commit()
```

## 📊 预期效果

### 性能对比

| 场景 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 首次查询 | 3-5 秒 | 3-5 秒 | - |
| 再次查询 | 3-5 秒 | <100ms | **95%+** |
| 缓存命中率 | - | 80-90% | - |

### 数据一致性

- **分红数据**：年度数据，变化频率低
- **缓存期**：7 天（可调）
- **一致性风险**：低（分红公告后才会变化）

## 🔧 实现步骤

### Step 1: 创建缓存表
```python
def init_dividend_cache_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dividend_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            dividend_data TEXT NOT NULL,
            cache_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expire_time TIMESTAMP,
            UNIQUE(stock_code)
        )
    ''')
    conn.commit()
```

### Step 2: 实现缓存函数
```python
def get_dividend_cached(code: str, force_refresh=False):
    # 查询缓存
    # 检查过期
    # 重新获取
    # 更新缓存
```

### Step 3: 修改接口
```python
# 替换 get_dividend_data 为 get_dividend_cached
```

### Step 4: 添加缓存管理
- 清理过期缓存
- 手动刷新接口（可选）

## ⚠️ 注意事项

1. **缓存失效场景**
   - 股票分红方案公告时
   - 除权除息日临近时
   - 用户手动刷新

2. **缓存容量**
   - 每条约 1-2KB（JSON）
   - 1000 只股票 ≈ 2MB
   - 定期清理过期数据

3. **并发安全**
   - SQLite 支持简单并发
   - 高并发场景考虑 Redis

## 📈 扩展方向

1. **分级缓存**
   - 内存缓存（LRU）：热点数据
   - SQLite 缓存：全量数据

2. **智能缓存**
   - 财报季缩短缓存期（1-3 天）
   - 非财报季延长缓存期（7-15 天）

3. **预加载**
   - 热门股票（ROE Top100）定期刷新
   - 用户自选股优先缓存
