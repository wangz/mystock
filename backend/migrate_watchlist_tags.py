"""
观察仓标签功能数据迁移脚本

功能：
1. 创建 user_tags 表
2. 迁移所有用户的 watchlist 数据格式（从 ["code1", "code2"] 转为 [{"code": "code1", "tags": []}]）
3. 为已有用户初始化预设标签

使用方法：
    python migrate_watchlist_tags.py
"""

import sqlite3
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB = os.path.join(os.path.dirname(BASE_DIR), "user_data.db")

# 预设标签
PRESET_TAGS = [
    {'name': '科技', 'color': '#409EFF', 'is_preset': True, 'is_enabled': True},
    {'name': '医药', 'color': '#67C23A', 'is_preset': True, 'is_enabled': True},
    {'name': '消费', 'color': '#E6A23C', 'is_preset': True, 'is_enabled': True},
    {'name': '金融', 'color': '#909399', 'is_preset': True, 'is_enabled': True},
    {'name': '地产', 'color': '#F56C6C', 'is_preset': True, 'is_enabled': False},
    {'name': '新能源', 'color': '#00C853', 'is_preset': True, 'is_enabled': True},
    {'name': 'AI', 'color': '#9C27B0', 'is_preset': True, 'is_enabled': False},
]


def create_user_tags_table():
    """创建 user_tags 表"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()
    print("✅ user_tags 表创建成功")


def init_preset_tags(conn, cursor, user_id: str):
    """为用户初始化预设标签（使用已有连接）"""
    for tag in PRESET_TAGS:
        cursor.execute('''
            INSERT OR IGNORE INTO user_tags (user_id, name, color, is_preset, is_enabled)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, tag['name'], tag['color'], 1 if tag['is_preset'] else 0, 1 if tag['is_enabled'] else 0))


def migrate_watchlist():
    """迁移 watchlist 数据格式"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取所有有 watchlist 的用户
    cursor.execute('''
        SELECT DISTINCT user_id, json_value 
        FROM user_data 
        WHERE data_type = 'watchlist'
    ''')
    users = cursor.fetchall()
    
    migrated_count = 0
    preset_init_count = 0
    
    for user_id, old_value in users:
        if not old_value:
            continue
            
        old_list = json.loads(old_value)
        
        # 检查是否已经是新格式
        if old_list and isinstance(old_list[0], dict) and 'code' in old_list[0]:
            print(f"  用户 {user_id}: 已是新格式，跳过")
            continue
        
        # 旧格式转换为新格式
        if old_list and isinstance(old_list[0], str):
            new_list = [{"code": code, "tags": []} for code in old_list]
        else:
            new_list = []
        
        # 更新 watchlist
        cursor.execute('''
            INSERT OR REPLACE INTO user_data 
            (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, 'watchlist', '', ?, ?)
        ''', (user_id, json.dumps(new_list), datetime.now()))
        
        # 为用户初始化预设标签（使用已有连接）
        init_preset_tags(conn, cursor, user_id)
        
        migrated_count += 1
        preset_init_count += 1
        print(f"  用户 {user_id}: 迁移完成 ({len(old_list)} 条 -> {len(new_list)} 条)")
    
    conn.commit()
    conn.close()
    
    return migrated_count, preset_init_count


def migrate_portfolio():
    """迁移 portfolio 数据格式（可选）"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT user_id, json_value 
        FROM user_data 
        WHERE data_type = 'portfolio'
    ''')
    users = cursor.fetchall()
    
    migrated_count = 0
    
    for user_id, old_value in users:
        if not old_value:
            continue
            
        old_list = json.loads(old_value)
        
        # 检查是否已经是新格式
        if old_list and isinstance(old_list[0], dict) and 'code' in old_list[0]:
            continue
        
        # 旧格式转换为新格式
        if old_list and isinstance(old_list[0], str):
            new_list = [{"code": code, "shares": 0} for code in old_list]
        else:
            new_list = []
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_data 
            (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, 'portfolio', '', ?, ?)
        ''', (user_id, json.dumps(new_list), datetime.now()))
        
        migrated_count += 1
    
    conn.commit()
    conn.close()
    
    return migrated_count


def main():
    print("=" * 50)
    print("观察仓标签功能数据迁移")
    print("=" * 50)
    
    # 检查数据库文件是否存在
    if not os.path.exists(USER_DB):
        print(f"❌ 数据库文件不存在: {USER_DB}")
        return
    
    print(f"\n📦 数据库: {USER_DB}")
    
    # 1. 创建表
    print("\n[1/3] 创建 user_tags 表...")
    create_user_tags_table()
    
    # 2. 迁移 watchlist
    print("\n[2/3] 迁移 watchlist 数据格式...")
    wl_count, preset_count = migrate_watchlist()
    print(f"  watchlist 迁移完成: {wl_count} 个用户")
    print(f"  预设标签初始化完成: {preset_count} 个用户")
    
    # 3. 迁移 portfolio（可选）
    print("\n[3/3] 迁移 portfolio 数据格式...")
    pf_count = migrate_portfolio()
    print(f"  portfolio 迁移完成: {pf_count} 个用户")
    
    print("\n" + "=" * 50)
    print("✅ 迁移完成！")
    print("=" * 50)
    print("\n后续操作：")
    print("1. 启动服务: python main.py")
    print("2. 测试标签功能")
    print("3. 如需回滚，删除 user_tags 表即可")


if __name__ == '__main__':
    main()
