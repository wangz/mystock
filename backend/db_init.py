"""
数据库初始化模块
"""

import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "portfolio_data.json")
MEMOS_FILE = os.path.join(BASE_DIR, "memos.json")
USER_DB = os.path.join(BASE_DIR, "user_data.db")

def init_database():
    """初始化用户数据库，创建 users 和 user_data 表"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            data_type TEXT NOT NULL,
            data_key TEXT DEFAULT '',
            json_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, data_type, data_key)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_lookup 
        ON user_data(user_id, data_type)
    ''')
    
    # 创建用户标签表
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
    logger.info("数据库表初始化完成")

def migrate_old_data():
    """迁移旧数据到用户数据库"""
    logger.info("开始数据迁移...")
    
    if not os.path.exists(DATA_FILE) and not os.path.exists(MEMOS_FILE):
        logger.info("没有找到需要迁移的数据文件，跳过迁移")
        return
    
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    migrated_count = 0
    
    # 迁移 portfolio_data.json
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 持仓
            if "portfolio" in data:
                portfolio = json.dumps(data["portfolio"])
                cursor.execute('''
                    INSERT OR REPLACE INTO user_data 
                    (user_id, data_type, data_key, json_value, updated_at)
                    VALUES ('default_user', 'portfolio', '', ?, ?)
                ''', (portfolio, datetime.now()))
                logger.info(f"迁移持仓: {len(data['portfolio'])} 条")
                migrated_count += 1
            
            # 观察列表
            if "watchlist" in data:
                watchlist = json.dumps(data["watchlist"])
                cursor.execute('''
                    INSERT OR REPLACE INTO user_data 
                    (user_id, data_type, data_key, json_value, updated_at)
                    VALUES ('default_user', 'watchlist', '', ?, ?)
                ''', (watchlist, datetime.now()))
                logger.info(f"迁移观察列表: {len(data['watchlist'])} 条")
                migrated_count += 1
            
            # 感悟
            if "insights" in data:
                insights = json.dumps(data["insights"])
                cursor.execute('''
                    INSERT OR REPLACE INTO user_data 
                    (user_id, data_type, data_key, json_value, updated_at)
                    VALUES ('default_user', 'insights', '', ?, ?)
                ''', (insights, datetime.now()))
                logger.info(f"迁移感悟: {len(data['insights'])} 条")
                migrated_count += 1
            
            # 历史记录
            if "history" in data:
                history = json.dumps(data["history"])
                cursor.execute('''
                    INSERT OR REPLACE INTO user_data 
                    (user_id, data_type, data_key, json_value, updated_at)
                    VALUES ('default_user', 'history', '', ?, ?)
                ''', (history, datetime.now()))
                logger.info(f"迁移历史记录: {len(data['history'])} 条")
                migrated_count += 1
            
            conn.commit()
            
            # 删除原文件
            os.remove(DATA_FILE)
            logger.info(f"已删除 portfolio_data.json")
            
        except Exception as e:
            logger.error(f"迁移 portfolio_data.json 失败: {e}")
    
    # 迁移 memos.json
    if os.path.exists(MEMOS_FILE):
        try:
            with open(MEMOS_FILE, 'r', encoding='utf-8') as f:
                memos = json.load(f)
            
            for ticker, memo_data in memos.items():
                memo_json = json.dumps(memo_data)
                cursor.execute('''
                    INSERT OR REPLACE INTO user_data 
                    (user_id, data_type, data_key, json_value, updated_at)
                    VALUES ('default_user', 'memos', ?, ?, ?)
                ''', (ticker, memo_json, datetime.now()))
            
            conn.commit()
            logger.info(f"迁移备忘录: {len(memos)} 条")
            
            # 删除原文件
            os.remove(MEMOS_FILE)
            logger.info("已删除 memos.json")
            
        except Exception as e:
            logger.error(f"迁移 memos.json 失败: {e}")
    
    conn.close()
    
    if migrated_count > 0:
        logger.info(f"数据迁移完成！共迁移 {migrated_count} 类数据")
    else:
        logger.info("没有数据需要迁移")

def init_all():
    """初始化数据库并迁移数据"""
    init_database()
    migrate_old_data()

if __name__ == "__main__":
    init_all()
