# 观察仓标签功能 - 任务清单

## 任务列表

### 阶段一：数据库设计

* [ ] **任务 1.1**：创建 user\_tags 表

  * 创建 `user_tags` 表结构

  * 添加索引

* [ ] **任务 1.2**：修改 user\_data 表的 watchlist 格式

  * 将 watchlist 从 `["code1", "code2"]` 改为 `[{"code": "code1", "tags": []}]`

  * 兼容旧数据迁移

* [ ] **任务 1.3**：预设标签初始化

  * 新用户注册时自动创建预设标签

### 阶段二：数据迁移

* [ ] **任务 2.1**：创建数据迁移脚本

  * 创建 `migrate_watchlist_tags.py`

  * 迁移现有 watchlist 数据格式

  * 为现有用户初始化预设标签

* [ ] **任务 2.2**：编写迁移脚本使用说明

  * 说明迁移前准备工作

  * 说明迁移步骤

  * 说明回滚步骤（可选）

### 阶段三：后端 API

* [ ] **任务 3.1**：实现 `GET /api/watchlist-tags`

  * 获取用户的所有标签（区分预设/自定义）

* [ ] **任务 3.2**：实现 `POST /api/watchlist-tags`

  * 创建自定义标签（验证名称唯一性）

* [ ] **任务 3.3**：实现 `PUT /api/watchlist-tags/{name}`

  * 启用/禁用预设标签

  * 更新自定义标签（名称、颜色）

* [ ] **任务 3.4**：实现 `DELETE /api/watchlist-tags/{name}`

  * 删除自定义标签

  * 从所有观察仓中移除该标签

* [ ] **任务 3.5**：修改 `GET /api/watchlist`

  * 返回数据包含 tags 字段

* [ ] **任务 3.6**：修改 `POST /api/watchlist/{code}`

  * 创建时支持可选的 tags 参数

* [ ] **任务 3.7**：实现 `PUT /api/watchlist-tags/{code}`

  * 更新指定股票的标签

### 阶段四：前端 UI

* [ ] **任务 4.1**：创建标签筛选栏

  * 显示已启用标签

  * 点击切换筛选

  * 显示/隐藏设置按钮

* [ ] **任务 4.2**：创建标签设置弹窗

  * 预设标签启用/禁用切换

  * 自定义标签列表

  * 添加自定义标签表单

* [ ] **任务 4.3**：修改观察列表表格

  * 添加标签列

  * 显示每只股票的标签

* [ ] **任务 4.4**：实现标签筛选逻辑

  * computed 属性过滤

  * 筛选状态指示器

* [ ] **任务 4.5**：修改添加股票弹窗

  * 添加标签选择区域

* [ ] **任务 4.6**：实现股票标签编辑

  * 点击标签打开编辑弹窗

***

## 任务依赖关系

```
阶段一（1.1-1.3）
    ↓
阶段二（2.1-2.2）← 依赖阶段一完成
    ↓
阶段三（3.1-3.7）← 依赖阶段一完成
    ↓
阶段四（4.1-4.6）← 依赖阶段三 API 完成
```

***

## 技术实现提示

### 后端

1. **user\_tags 表初始化**：

```python
def init_preset_tags(user_id):
    preset_tags = [
        ('科技', '#409EFF', 1, 1),
        ('医药', '#67C23A', 1, 1),
        ('消费', '#E6A23C', 1, 1),
        ('金融', '#909399', 1, 1),
        ('地产', '#F56C6C', 1, 0),
        ('新能源', '#00C853', 1, 1),
        ('AI', '#9C27B0', 1, 0),
    ]
    # INSERT INTO user_tags ...
```

1. **观察列表数据格式**：

```python
# 旧格式
["sh600519", "sz300054"]

# 新格式
[
    {"code": "sh600519", "tags": ["科技", "消费"]},
    {"code": "sz300054", "tags": ["化工"]}
]
```

1. **删除标签时清理观察列表**：

```python
def remove_tag_from_watchlist(user_id, tag_name):
    watchlist = get_watchlist_codes(user_id)  # 返回新格式
    for item in watchlist:
        if tag_name in item['tags']:
            item['tags'].remove(tag_name)
    save_watchlist(user_id, watchlist)
```

### 数据迁移脚本

```python
# migrate_watchlist_tags.py

USER_DB = 'user_data.db'

def migrate_watchlist_format():
    """迁移 watchlist 数据格式"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 1. 创建 user_tags 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#409EFF',
            is_preset INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_tags_lookup 
        ON user_tags(user_id, is_enabled)
    ''')
    
    # 2. 获取所有有 watchlist 的用户
    cursor.execute('''
        SELECT DISTINCT user_id, json_value 
        FROM user_data 
        WHERE data_type = 'watchlist'
    ''')
    users = cursor.fetchall()
    
    # 3. 迁移每个用户的 watchlist
    for user_id, old_value in users:
        # 旧格式: ["sh600519", "sz300054"]
        # 新格式: [{"code": "sh600519", "tags": []}]
        old_list = json.loads(old_value) if old_value else []
        new_list = [{"code": code, "tags": []} for code in old_list]
        
        # 更新 watchlist
        cursor.execute('''
            INSERT OR REPLACE INTO user_data 
            (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, 'watchlist', '', ?, ?)
        ''', (user_id, json.dumps(new_list), datetime.now()))
        
        # 为用户创建预设标签
        init_preset_tags_for_user(cursor, user_id)
    
    conn.commit()
    conn.close()
    print(f"迁移完成，共处理 {len(users)} 个用户")

if __name__ == '__main__':
    migrate_watchlist_format()
```

### 前端

1. **状态变量**：

```javascript
const userTags = ref([]);           // 用户所有标签
const enabledTags = computed(() => userTags.value.filter(t => t.is_enabled));
const selectedTag = ref(null);      // 当前筛选标签
const showTagSettings = ref(false); // 设置弹窗
```

1. **筛选逻辑**：

```javascript
const filteredWatchlist = computed(() => {
    if (!selectedTag.value) return watchlist.value;
    return watchlist.value.filter(s => s.tags?.includes(selectedTag.value));
});
```

