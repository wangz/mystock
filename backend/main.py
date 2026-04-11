from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import json
import os
import requests
import httpx
import asyncio
import akshare as ak

from simple_limit_up import SimpleLimitUpAnalyzer
from baostock_fetcher import batch_get_prices, get_stock_price
from db_init import init_all
from auth import (
    get_current_user, get_optional_user,
    create_token, verify_password,
    get_user_by_email, create_user, update_last_login
)
from models import RegisterRequest, LoginRequest, TokenResponse, UserInfo, ChangePasswordRequest

app = FastAPI(title="MyStock API", version="2.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据文件路径（使用绝对路径）
import os
import sqlite3
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库文件路径
FINANCE_DB = os.path.join(BASE_DIR, "finance_data.db")    # 股票基础数据
USER_DB = os.path.join(BASE_DIR, "user_data.db")           # 用户数据
CACHE_DB = os.path.join(BASE_DIR, "cache.db")              # 统一缓存数据库
DEFAULT_USER_ID = 'default_user'  # 默认用户ID，未登录时使用

# 缓存配置
CACHE_DURATION_VERY_SHORT = 60       # 1分钟缓存（秒）
CACHE_DURATION_SHORT = 60 * 60       # 1小时缓存（秒）
CACHE_DURATION_LONG = 1 * 24 * 60 * 60  # 1天缓存（秒）

def init_cache_table():
    """初始化统一缓存表"""
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                data_type TEXT,
                json_data TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expire_at TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expire ON cache(expire_at)')
        
        conn.commit()
        conn.close()
        print("✅ 缓存表初始化完成")
    except Exception as e:
        print(f"创建缓存表失败：{e}")

def get_cache(cache_key: str) -> tuple:
    """
    获取缓存数据
    :param cache_key: 缓存键
    :return: (数据, 是否缓存, 缓存时间)
    """
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT json_data, cached_at FROM cache WHERE cache_key = ?
        ''', (cache_key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = json.loads(row[0])
            cached_at = datetime.fromisoformat(row[1])
            return data, True, cached_at
        return None, False, None
    except Exception as e:
        print(f"获取缓存失败: {e}")
        return None, False, None

def set_cache(cache_key: str, data_type: str, data, duration: int = CACHE_DURATION_SHORT):
    """
    设置缓存
    :param cache_key: 缓存键
    :param data_type: 数据类型
    :param data: 缓存数据
    :param duration: 缓存时长（秒）
    """
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        expire_at = datetime.now() + timedelta(seconds=duration)
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache (cache_key, data_type, json_data, cached_at, expire_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (cache_key, data_type, json.dumps(data, ensure_ascii=False), datetime.now(), expire_at))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"设置缓存失败: {e}")

def clean_expired_cache():
    """清理过期缓存"""
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache WHERE expire_at < ?', (datetime.now(),))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        if deleted > 0:
            print(f"🗑️ 清理了 {deleted} 条过期缓存")
    except Exception as e:
        print(f"清理过期缓存失败：{e}")

def load_stock_codes():
    """加载股票代码信息"""
    try:
        conn = sqlite3.connect(FINANCE_DB)
        cursor = conn.cursor()
        
        cursor.execute('SELECT code, name, aliases FROM stock_codes')
        stock_codes = {}
        
        for row in cursor.fetchall():
            code, name, aliases_json = row
            aliases = json.loads(aliases_json) if aliases_json else []
            stock_codes[code] = {
                'name': name,
                'aliases': aliases
            }
        
        conn.close()
        return stock_codes
    except Exception as e:
        print(f"加载 stock_codes 失败: {e}")
        return {}

def get_roe_data(code):
    """从数据库获取股票的ROE数据"""
    try:
        conn = sqlite3.connect(FINANCE_DB)
        cursor = conn.cursor()

        # 直接使用 code 查询
        cursor.execute('SELECT date, roe FROM roe_data WHERE code = ? ORDER BY date DESC', (code,))
        roe_records = cursor.fetchall()

        conn.close()

        return [{'date': date, 'roe': roe} for date, roe in roe_records]
    except Exception as e:
        print(f"获取ROE数据失败: {e}")
        return []

# Pydantic 模型
class Stock(BaseModel):
    ticker: str
    code: str  # 市场代码，如 sz000725

class PortfolioResponse(BaseModel):
    portfolio: List[dict]
    watchlist: List[dict]
    stock_codes: dict

class StockData(BaseModel):
    ticker: str
    price: float
    change: float
    change_percent: float

# 获取股票数据（腾讯API）
def get_stock_data(ticker: str, code: str) -> Optional[dict]:
    try:
        url = f"https://qt.gtimg.cn/q={code}"
        response = requests.get(url, timeout=3)

        if response.status_code == 200 and response.content:
            # 尝试GBK编码（腾讯API使用GBK）
            try:
                data = response.content.decode('gbk', errors='ignore')
            except:
                data = response.text

            if '=' in data:
                parts = data.split('="')[1].rstrip('";')
                fields = parts.split('~')

                if len(fields) > 32:
                    current_price = float(fields[3])
                    previous_close = float(fields[4])
                    change = float(fields[31])
                    change_percent = float(fields[32])

                    if current_price > 0:
                        return {
                            'ticker': ticker,
                            'code': code,
                            'name': fields[1],
                            'price': current_price,
                            'previous_close': previous_close,
                            'change': change,
                            'change_percent': change_percent
                        }
        return None
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {e}")
        return None


def get_stocks_data_batch(stocks: list) -> dict:
    """
    批量获取股票数据（一次性请求）
    stocks: [{'name': '贵州茅台', 'code': 'sh600519'}, ...]
    返回: {'sh600519': {...}, 'sz000858': {...}, ...}
    """
    if not stocks:
        return {}

    codes = [s['code'] for s in stocks]
    name_map = {s['code']: s['name'] for s in stocks}

    try:
        url = f"https://qt.gtimg.cn/q={','.join(codes)}"
        response = requests.get(url, timeout=5)

        result = {}
        if response.status_code == 200 and response.content:
            try:
                data = response.content.decode('gbk', errors='ignore')
            except:
                data = response.text

            for line in data.strip().split(';'):
                line = line.strip()  # 去掉前后空白
                if not line or '=' not in line:
                    continue

                try:
                    # 从 v_sh600519 提取代码
                    code_part = line.split('="')[0].replace('v_', '')
                    parts = line.split('="')[1].rstrip('";')
                    fields = parts.split('~')

                    if len(fields) > 32:
                        # 使用 code_part（如 sh600519）而不是 fields[2]（600519）
                        code = code_part
                        current_price = float(fields[3])
                        previous_close = float(fields[4])
                        change = float(fields[31])
                        change_percent = float(fields[32])

                        if current_price > 0:
                            result[code] = {
                                'ticker': name_map.get(code, code),
                                'code': code,
                                'name': fields[1],
                                'price': current_price,
                                'previous_close': previous_close,
                                'change': change,
                                'change_percent': change_percent
                            }
                except (IndexError, ValueError) as e:
                    continue

        return result
    except Exception as e:
        print(f"批量获取股票数据失败: {e}")
        return {}


def fetch_stock_data_async(ticker: str, code: str):
    return get_stock_data(ticker, code)

# API 路由
@app.get("/")
def root():
    return {"message": "MyStock API", "version": "2.0.0"}

# 获取股票列表（快速返回，不调用外部API）

def get_user_stock_list(user_id: str, data_type: str) -> list:
    """从数据库获取用户的股票列表（portfolio 或 watchlist）"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?',
                   (user_id, data_type))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def load_memos(user_id=None):
    """加载备忘录数据（支持按用户加载）"""
    if user_id:
        # 从数据库加载用户的备忘录
        try:
            conn = sqlite3.connect(USER_DB)
            cursor = conn.cursor()
            
            cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                           (user_id, 'memos'))
            row = cursor.fetchone()
            conn.close()
            
            return json.loads(row[0]) if row else {}
        except Exception as e:
            print(f"加载用户备忘录失败: {e}")
            return {}
    else:
        # 从默认用户加载备忘录（向后兼容）
        try:
            conn = sqlite3.connect(USER_DB)
            cursor = conn.cursor()
            
            cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                           ('default_user', 'memos'))
            row = cursor.fetchone()
            conn.close()
            
            return json.loads(row[0]) if row else {}
        except Exception as e:
            print(f"加载默认备忘录失败: {e}")
            return {}



# 异步获取单只股票数据
def fetch_stock_data_async(ticker: str, code: str):
    return get_stock_data(ticker, code)

# 获取股票的ROE数据
@app.get("/api/roe-data/{code}")
def get_stock_roe(code: str):
    """获取股票的ROE数据"""
    try:
        roe_data = get_roe_data(code)
        stock_codes = load_stock_codes()
        name = stock_codes.get(code, {}).get('name', code)
        
        return {
            "code": code,
            "name": name,
            "roe_data": roe_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取ROE数据失败: {str(e)}")

# 添加持仓
@app.post("/api/portfolio/{ticker}")
def add_portfolio(ticker: str, current_user: dict = Depends(get_current_user)):
    """添加持仓（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前持仓
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'portfolio'))
    row = cursor.fetchone()
    portfolio_codes = json.loads(row[0]) if row else []
    
    # 检查股票代码是否存在
    stock_codes = load_stock_codes()
    if ticker not in stock_codes:
        conn.close()
        raise HTTPException(status_code=400, detail="股票代码不存在")
    
    # 检查是否已在持仓中
    if ticker in portfolio_codes:
        conn.close()
        raise HTTPException(status_code=400, detail="股票已在持仓中")
    
    # 添加到持仓
    portfolio_codes.append(ticker)
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'portfolio', json.dumps(portfolio_codes), datetime.now()))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"已添加 {ticker} 到持仓"}

# 移除持仓
@app.delete("/api/portfolio/{ticker}")
def remove_portfolio(ticker: str, current_user: dict = Depends(get_current_user)):
    """移除持仓（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前持仓
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'portfolio'))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="股票不在持仓中")
    
    portfolio_codes = json.loads(row[0])
    if ticker not in portfolio_codes:
        conn.close()
        raise HTTPException(status_code=404, detail="股票不在持仓中")
    
    # 从持仓中移除
    portfolio_codes.remove(ticker)
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'portfolio', json.dumps(portfolio_codes), datetime.now()))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"已移除 {ticker}"}

# 添加观察列表
@app.post("/api/watchlist/{ticker}")
def add_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    """添加观察列表（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前观察列表
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'watchlist'))
    row = cursor.fetchone()
    watchlist_codes = json.loads(row[0]) if row else []
    
    # 检查股票代码是否存在
    stock_codes = load_stock_codes()
    if ticker not in stock_codes:
        conn.close()
        raise HTTPException(status_code=400, detail="股票代码不存在")
    
    # 检查是否已在观察列表中
    if ticker in watchlist_codes:
        conn.close()
        raise HTTPException(status_code=400, detail="股票已在观察列表中")
    
    # 添加到观察列表
    watchlist_codes.append(ticker)
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'watchlist', json.dumps(watchlist_codes), datetime.now()))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"已添加 {ticker} 到观察列表"}

# 移除观察列表
@app.delete("/api/watchlist/{ticker}")
def remove_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    """移除观察列表（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前观察列表
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'watchlist'))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="股票不在观察列表中")
    
    watchlist_codes = json.loads(row[0])
    if ticker not in watchlist_codes:
        conn.close()
        raise HTTPException(status_code=404, detail="股票不在观察列表中")
    
    # 从观察列表中移除
    watchlist_codes.remove(ticker)
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'watchlist', json.dumps(watchlist_codes), datetime.now()))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"已移除 {ticker}"}

# 感悟管理
@app.get("/api/insights")
def get_insights(current_user: Optional[dict] = Depends(get_optional_user)):
    """获取感悟（支持登录和未登录状态）"""
    user_id = current_user['user_id'] if current_user else DEFAULT_USER_ID
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'insights'))
    row = cursor.fetchone()
    conn.close()
    
    insights = json.loads(row[0]) if row else []
    
    return {
        "insights": insights,
        "count": len(insights)
    }

@app.post("/api/insights")
def add_insight(insight: dict, current_user: dict = Depends(get_current_user)):
    """添加感悟（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前感悟
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'insights'))
    row = cursor.fetchone()
    insights = json.loads(row[0]) if row else []

    insights.insert(0, insight)  # 新感悟插入到最前面

    # 只保留最近100条
    if len(insights) > 100:
        insights = insights[:100]

    # 保存到数据库
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'insights', json.dumps(insights), datetime.now()))
    
    conn.commit()
    conn.close()

    return {
        "success": True,
        "insights": insights,
        "count": len(insights)
    }

@app.delete("/api/insights/{index}")
def delete_insight(index: int, current_user: dict = Depends(get_current_user)):
    """删除感悟（需登录）"""
    user_id = current_user['user_id']
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前感悟
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'insights'))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="感悟不存在")
    
    insights = json.loads(row[0])
    if 0 <= index < len(insights):
        insights.pop(index)
        
        # 保存到数据库
        cursor.execute('''
            INSERT OR REPLACE INTO user_data 
            (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, ?, '', ?, ?)
        ''', (user_id, 'insights', json.dumps(insights), datetime.now()))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "insights": insights,
            "count": len(insights)
        }
    else:
        conn.close()
        raise HTTPException(status_code=404, detail="感悟索引不存在")

# 保存股票排序
@app.post("/api/stock-order/{list_name}")
def save_stock_order(list_name: str, order_data: dict, current_user: dict = Depends(get_current_user)):
    """保存股票排序（需登录，直接操作数据库）"""
    if list_name not in ['portfolio', 'watchlist']:
        raise HTTPException(status_code=400, detail="无效的列表名称")

    user_id = current_user['user_id']
    order = order_data.get('order', [])

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, list_name, json.dumps(order), datetime.now()))

    conn.commit()
    conn.close()

    return {"success": True}

# 添加到历史记录
@app.post("/api/stock-history")
def add_to_history(stock_data: dict, current_user: dict = Depends(get_current_user)):
    """添加删除的股票到历史记录（需登录）"""
    user_id = current_user['user_id']
    code = stock_data.get('code')
    name = stock_data.get('name')

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    # 获取现有历史
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'history'))
    row = cursor.fetchone()
    history = json.loads(row[0]) if row else []

    # 检查是否已经存在
    existing = [h for h in history if h.get('code') == code]
    if existing:
        for h in existing:
            h['deleted_at'] = datetime.now().isoformat()
    else:
        history_entry = {
            'name': name,
            'code': code,
            'from': stock_data.get('from'),
            'deleted_at': datetime.now().isoformat()
        }
        history.insert(0, history_entry)

    # 只保留最近100条
    if len(history) > 100:
        history = history[:100]

    cursor.execute('''
        INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, 'history', '', ?, ?)
    ''', (user_id, json.dumps(history), datetime.now()))

    conn.commit()
    conn.close()

    return {"success": True, "history": history}

# 获取历史记录
@app.get("/api/stock-history")
def get_history(current_user: Optional[dict] = Depends(get_optional_user)):
    """获取删除历史（支持登录和未登录状态）"""
    user_id = current_user['user_id'] if current_user else DEFAULT_USER_ID

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'history'))
    row = cursor.fetchone()
    history = json.loads(row[0]) if row else []

    conn.close()

    return {"history": history, "count": len(history)}

# 恢复股票
@app.post("/api/stock-restore")
def restore_stock(restore_data: dict, current_user: dict = Depends(get_current_user)):
    """恢复删除的股票（需登录）"""
    user_id = current_user['user_id']
    code = restore_data.get('code')
    from_list = restore_data.get('from')
    history_index = restore_data.get('history_index')

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    # 添加到原列表
    cursor.execute(f'SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, from_list))
    row = cursor.fetchone()
    stock_list = json.loads(row[0]) if row else []

    if code not in stock_list:
        stock_list.append(code)
        cursor.execute('''
            INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, ?, '', ?, ?)
        ''', (user_id, from_list, json.dumps(stock_list), datetime.now()))

    # 从历史记录中删除
    if history_index is not None:
        cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'history'))
        row = cursor.fetchone()
        history = json.loads(row[0]) if row else []

        if 0 <= history_index < len(history):
            history.pop(history_index)
            cursor.execute('''
                INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
                VALUES (?, 'history', '', ?, ?)
            ''', (user_id, json.dumps(history), datetime.now()))

    conn.commit()
    conn.close()

    return {"success": True}

# 删除历史记录
@app.delete("/api/stock-history/{index}")
def delete_history(index: int, current_user: dict = Depends(get_current_user)):
    """删除历史记录（需登录）"""
    user_id = current_user['user_id']

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'history'))
    row = cursor.fetchone()
    history = json.loads(row[0]) if row else []

    if 0 <= index < len(history):
        history.pop(index)
        cursor.execute('''
            INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
            VALUES (?, 'history', '', ?, ?)
        ''', (user_id, json.dumps(history), datetime.now()))
        conn.commit()
        conn.close()
        return {"success": True}
    else:
        conn.close()
        raise HTTPException(status_code=404, detail="历史记录不存在")

# 保存股票备忘
@app.post("/api/stock-memo")
def save_memo(memo_data: dict, current_user: dict = Depends(get_current_user)):
    """保存股票备忘（需登录）"""
    user_id = current_user['user_id']
    name = memo_data.get('name')
    code = memo_data.get('code')
    memo = memo_data.get('memo', '')

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # 获取用户当前备忘
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'memos'))
    row = cursor.fetchone()
    memos = json.loads(row[0]) if row else {}

    if memo and code:
        memos[code] = {
            'name': name,
            'memo': memo,
            'updated_at': datetime.now().isoformat()
        }
    elif code in memos:
        del memos[code]

    # 保存到数据库
    cursor.execute('''
        INSERT OR REPLACE INTO user_data 
        (user_id, data_type, data_key, json_value, updated_at)
        VALUES (?, ?, '', ?, ?)
    ''', (user_id, 'memos', json.dumps(memos), datetime.now()))
    
    conn.commit()
    conn.close()

    return {"success": True, "memos": memos}

# 获取所有备忘
@app.get("/api/stock-memo")
def get_memos(current_user: Optional[dict] = Depends(get_optional_user)):
    """获取股票备忘（支持登录和未登录状态）"""
    user_id = current_user['user_id'] if current_user else DEFAULT_USER_ID
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', 
                   (user_id, 'memos'))
    row = cursor.fetchone()
    conn.close()
    
    memos = json.loads(row[0]) if row else {}
    
    return {"memos": memos}

# 获取所有股票代码
@app.get("/api/all-stock-codes")
def get_all_stock_codes():
    """获取所有已知的股票代码"""
    stock_codes = load_stock_codes()
    return {"stock_codes": stock_codes}

# 搜索股票
@app.get("/api/search-stock")
def search_stock(keyword: str):
    """搜索股票（后端备用，实际由前端直接调用）"""
    try:
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": "14",
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": "10"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        text = response.text

        results = []
        try:
            data = json.loads(text)
            if data and 'QuotationCodeTable' in data:
                table_data = data['QuotationCodeTable']
                if table_data and 'Data' in table_data:
                    for item in table_data['Data']:
                        if isinstance(item, dict):
                            results.append({
                                'name': item.get('Name', ''),
                                'code': item.get('Code', ''),
                                'type': item.get('SecurityTypeName', '')
                            })
        except:
            pass

        return {"results": results[:10]}
    except:
        return {"results": []}

# 添加股票
@app.post("/api/add-stock")
def add_stock(stock_data: dict, current_user: dict = Depends(get_current_user)):
    """添加股票到持仓或观察（需登录）"""
    user_id = current_user['user_id']
    
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    code = stock_data.get('code')
    target = stock_data.get('target')
    
    # 获取当前用户数据
    if target == 'portfolio':
        cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'portfolio'))
        row = cursor.fetchone()
        portfolio_list = json.loads(row[0]) if row else []
        
        if code not in portfolio_list:
            portfolio_list.append(code)
            cursor.execute('''
                INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
                VALUES (?, 'portfolio', '', ?, ?)
            ''', (user_id, json.dumps(portfolio_list), datetime.now()))
    else:
        cursor.execute('SELECT json_value FROM user_data WHERE user_id = ? AND data_type = ?', (user_id, 'watchlist'))
        row = cursor.fetchone()
        watchlist = json.loads(row[0]) if row else []
        
        if code not in watchlist:
            watchlist.append(code)
            cursor.execute('''
                INSERT OR REPLACE INTO user_data (user_id, data_type, data_key, json_value, updated_at)
                VALUES (?, 'watchlist', '', ?, ?)
            ''', (user_id, json.dumps(watchlist), datetime.now()))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"已将 {code} 添加到{target}"}

@app.get("/api/limit-up-analysis")
def get_limit_up_analysis(refresh: bool = False):
    """
    获取涨停板分析报告（使用问财数据）
    包括：
    - 当日首板股票总数
    - 首板候选股票列表（含涨停时间、评分、特征等）
    - 时间分布统计
    """
    if not refresh:
        cached_data, is_cached, cached_at = get_cache('limit_up_analysis')
        if is_cached and cached_data:
            cached_data['cached'] = True
            cached_data['cached_at'] = cached_at.isoformat() if cached_at else None
            return cached_data

    analyzer = SimpleLimitUpAnalyzer()
    analysis = analyzer.get_full_analysis()
    analysis['cached'] = False
    set_cache('limit_up_analysis', 'limit_up', analysis, CACHE_DURATION_VERY_SHORT)
    return analysis

@app.get("/api/shareholder-activity")
def get_shareholder_activity(refresh: bool = False):
    """
    获取股东动态数据（增持、回购）
    包括：
    - 股东增持列表
    - 股票回购列表
    - 高管增持列表
    """
    # 尝试从缓存获取
    if not refresh:
        cached_data, is_cached, cached_at = get_cache('shareholder_activity')
        if is_cached and cached_data:
            cached_data['cached'] = True
            cached_data['cached_at'] = cached_at.isoformat() if cached_at else None
            return cached_data

    try:
        import pywencai
        import numpy as np

        def clean_data(value):
            if isinstance(value, (float, np.floating)):
                if np.isnan(value) or np.isinf(value):
                    return None
            return value

        def clean_record(record):
            return {k: clean_data(v) for k, v in record.items()}

        def standardize_column_name(col_name):
            import re
            match = re.match(r'^(.+)\[\d{8}(?:-\d{8})?\]$', col_name)
            if match:
                return match.group(1)
            return col_name

        def standardize_record(record):
            new_record = {}
            for k, v in record.items():
                new_key = standardize_column_name(k)
                if new_key not in new_record:
                    new_record[new_key] = clean_data(v)
            return new_record

        def sort_by_field(items, field, reverse=True):
            return sorted(items, key=lambda x: float(x.get(field) or 0), reverse=reverse)

        result = {
            'timestamp': datetime.now().isoformat(),
            'cached': False
        }

        # 1. 股东增持
        try:
            df = pywencai.get(query='股东增持', loop=True, max_retries=2)
            if df is not None and not df.empty:
                items = [standardize_record(r) for r in df.to_dict('records')]
                items = sort_by_field(items, '大股东变动市值合计', True)
                result['shareholding_increase'] = {
                    'total': len(df),
                    'items': items
                }
            else:
                result['shareholding_increase'] = {'total': 0, 'items': []}
        except Exception as e:
            result['shareholding_increase'] = {'total': 0, 'items': [], 'error': str(e)}

        # 2. 股票回购
        try:
            df = pywencai.get(query='股票回购', loop=True, max_retries=2)
            if df is not None and not df.empty:
                items = [standardize_record(r) for r in df.to_dict('records')]
                items = sort_by_field(items, '拟回购资金总额', True)
                result['buyback'] = {
                    'total': len(df),
                    'items': items
                }
            else:
                result['buyback'] = {'total': 0, 'items': []}
        except Exception as e:
            result['buyback'] = {'total': 0, 'items': [], 'error': str(e)}

        # 3. 高管增持
        try:
            df = pywencai.get(query='高管增持', loop=True, max_retries=2)
            if df is not None and not df.empty:
                items = [standardize_record(r) for r in df.to_dict('records')]
                items = sort_by_field(items, '高管变动市值合计', True)
                result['executive_increase'] = {
                    'total': len(df),
                    'items': items
                }
            else:
                result['executive_increase'] = {'total': 0, 'items': []}
        except Exception as e:
            result['executive_increase'] = {'total': 0, 'items': [], 'error': str(e)}

        # 保存缓存
        set_cache('shareholder_activity', 'shareholder_activity', result, CACHE_DURATION_SHORT)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@app.get("/api/double-five-stocks")
def get_double_five_stocks(refresh: bool = False):
    """
    获取"双五"股票（PE<8 且 股息率>4%）
    双五指：PE接近8，股息率接近4%
    """
    if not refresh:
        cached_data, is_cached, cached_at = get_cache('double_five_stocks')
        if is_cached and cached_data:
            cached_data['cached'] = True
            cached_data['cached_at'] = cached_at.isoformat() if cached_at else None
            return cached_data

    try:
        import pywencai
        import numpy as np
        import re

        def clean_data(value):
            if isinstance(value, (float, np.floating)):
                if np.isnan(value) or np.isinf(value):
                    return None
            return value

        def standardize_column_name(col_name):
            """标准化列名，去掉动态日期范围后缀"""
            import re
            match = re.match(r'^(.+)\[\d{8}(?:-\d{8})?\]$', col_name)
            if match:
                return match.group(1)
            return col_name

        def standardize_record(record):
            """标准化记录，将所有列名去掉日期范围后缀"""
            new_record = {}
            for k, v in record.items():
                new_key = standardize_column_name(k)
                if new_key not in new_record:
                    new_record[new_key] = clean_data(v)
            return new_record

        # 查询双五股票
        df = pywencai.get(query='PE>0,PE<8,股息率>4', loop=True, max_retries=2)

        result = {
            'timestamp': datetime.now().isoformat(),
            'condition': 'PE<8 且 股息率>4%',
            'description': 'PE接近8，股息率接近4%',
            'total': 0,
            'items': []
        }

        if df is not None and not df.empty:
            items = [standardize_record(r) for r in df.to_dict('records')]
            result['total'] = len(items)
            result['items'] = items

        result['cached'] = False
        set_cache('double_five_stocks', 'stock_screening', result, CACHE_DURATION_SHORT)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


@app.get("/api/r15-stocks")
def get_r15_stocks(refresh: bool = False):
    """
    获取 R15 股票
    条件：近10年平均ROE > 15% 且 最低年份ROE > 10%
    """
    if not refresh:
        cached_data, is_cached, cached_at = get_cache('r15_stocks')
        if is_cached and cached_data:
            cached_data['cached'] = True
            cached_data['cached_at'] = cached_at.isoformat() if cached_at else None
            return cached_data

    try:
        conn = sqlite3.connect(FINANCE_DB)
        cursor = conn.cursor()

        # 查询满足条件的股票
        cursor.execute('''
            SELECT
                s.code,
                c.name,
                s.avg_roe_10y,
                s.avg_roe_5y,
                s.roe_latest,
                s.years_count,
                (
                    SELECT MIN(r2.roe)
                    FROM roe_data r2
                    WHERE r2.code = s.code
                    AND r2.date LIKE '%1231'
                    AND r2.date >= '20151231'
                    AND r2.roe > 0 AND r2.roe < 100
                ) as min_roe_10y
            FROM stock_roe_summary s
            LEFT JOIN stock_codes c ON s.code = c.code
            WHERE s.avg_roe_10y > 15
            AND s.years_count >= 8
            AND (
                SELECT MIN(r3.roe)
                FROM roe_data r3
                WHERE r3.code = s.code
                AND r3.date LIKE '%1231'
                AND r3.date >= '20151231'
                AND r3.roe > 0 AND r3.roe < 100
            ) > 14
            ORDER BY s.avg_roe_10y DESC
        ''')

        items = []
        for row in cursor.fetchall():
            code, name, avg_10y, avg_5y, roe_latest, years_count, min_roe = row
            items.append({
                'code': code,
                'name': name or '-',
                'avg_roe_10y': round(avg_10y, 2) if avg_10y else None,
                'avg_roe_5y': round(avg_5y, 2) if avg_5y else None,
                'roe_latest': round(roe_latest, 2) if roe_latest else None,
                'years_count': years_count,
                'min_roe_10y': round(min_roe, 2) if min_roe else None
            })

        conn.close()

        result = {
            'timestamp': datetime.now().isoformat(),
            'condition': '10年平均ROE>15% 且 最低年份ROE>10%',
            'total': len(items),
            'items': items,
            'cached': False
        }

        set_cache('r15_stocks', 'stock_screening', result, CACHE_DURATION_SHORT)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def get_dividend_data(code: str, years: int = 10):
    """
    使用 akshare 获取股票历年分红明细及派息率
    """
    def to_native(val):
        """将 numpy/pandas 类型转换为 Python 原生类型"""
        import math
        from datetime import date
        if val is None:
            return None
        try:
            if hasattr(val, 'item'):
                val = val.item()
            elif hasattr(val, 'tolist'):
                val = val.tolist()
            elif isinstance(val, date):
                return val.strftime('%Y-%m-%d')
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    return None
            return val
        except:
            return None
    
    # 注：原腾讯API函数已注释掉，使用外部导入的BaoStock函数
    # batch_get_prices函数现在从baostock_fetcher模块导入
    
    # 注：原腾讯API函数已注释掉，使用外部导入的BaoStock函数
    # get_stock_price函数现在从baostock_fetcher模块导入
    
    try:
        stock_code = code.replace('.SH', '').replace('.SZ', '').replace('sh', '').replace('sz', '')
        
        df = ak.stock_history_dividend_detail(symbol=stock_code)
        if df is None or len(df) == 0:
            return []
        
        dividend_list = []
        current_year = datetime.now().year
        cutoff_year = current_year - years
        
        # 收集所有需要查询价格的日期
        price_dates = []
        dividend_records = []
        
        for _, row in df.iterrows():
            progress = to_native(row.get('进度'))
            if progress != '实施':
                continue
            
            announce_date = to_native(row.get('公告日期'))
            ex_div_date = to_native(row.get('除权除息日'))
            cash_div_raw = to_native(row.get('派息'))
            cash_div = cash_div_raw / 10 if cash_div_raw else 0
            
            if not cash_div or cash_div <= 0:
                continue
            
            year = 0
            if ex_div_date:
                try:
                    year = int(str(ex_div_date)[:4])
                except:
                    pass
            elif announce_date:
                try:
                    year = int(str(announce_date)[:4])
                except:
                    pass
            
            if year < cutoff_year:
                continue
            
            if ex_div_date and isinstance(ex_div_date, str) and len(ex_div_date) >= 8:
                # 统一日期格式为 YYYYMMDD
                clean_date = ex_div_date.replace('/', '').replace('-', '')
                if len(clean_date) == 8:
                    price_dates.append(clean_date)
            
            dividend_records.append({
                'announce_date': announce_date if announce_date else '',
                'cash_div': round(cash_div, 2) if cash_div else 0,
                'ex_div_date': ex_div_date if ex_div_date else '',
                'progress': progress if progress else '',
                'year': year
            })
        
        # 批量获取所有价格
        price_map = batch_get_prices(stock_code, price_dates)
        
        # 组装最终结果
        for record in dividend_records:
            dividend_yield = None
            if record['ex_div_date'] and isinstance(record['ex_div_date'], str) and len(record['ex_div_date']) >= 8:
                # 统一日期格式为 YYYYMMDD
                clean_date = record['ex_div_date'].replace('/', '').replace('-', '')
                if len(clean_date) == 8:
                    price = price_map.get(clean_date)
                    if price and price > 0:
                        dividend_yield = round((record['cash_div'] / price) * 100, 2)
            
            dividend_list.append({
                'announce_date': record['announce_date'],
                'cash_div': record['cash_div'],
                'ex_div_date': record['ex_div_date'],
                'progress': record['progress'],
                'dividend_yield': dividend_yield
            })
        
        return dividend_list
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


@app.get("/api/stock-dividend/{code}")
def get_stock_dividend(code: str, refresh: bool = False):
    """获取股票分红数据（带缓存）"""
    cache_key = f'dividend_{code}'
    
    # 尝试从缓存获取
    if not refresh:
        cached_data, is_cached, cached_at = get_cache(cache_key)
        if is_cached and cached_data:
            return {
                'dividend_list': cached_data,
                'cached': True,
                'cached_at': cached_at.isoformat() if cached_at else None
            }
    
    # 获取新数据
    dividend_list = get_dividend_data(code, years=10)
    
    # 保存缓存
    set_cache(cache_key, 'dividend', dividend_list, CACHE_DURATION_LONG)
    
    return {
        'dividend_list': dividend_list,
        'cached': False
    }


@app.post("/api/cache/refresh/{code}")
def refresh_dividend_cache(code: str):
    """手动刷新分红缓存"""
    try:
        cache_key = f'dividend_{code}'
        dividend_list = get_dividend_data(code, years=10)
        set_cache(cache_key, 'dividend', dividend_list, CACHE_DURATION_LONG)
        return {'status': 'success', 'count': len(dividend_list)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.get("/api/stock-detail/{code}")
def get_stock_detail(code: str):
    """
    获取单只股票详情
    """
    try:
        conn = sqlite3.connect(FINANCE_DB)
        cursor = conn.cursor()

        result = {'code': code}

        cursor.execute('''
            SELECT name, aliases FROM stock_codes WHERE code = ?
        ''', (code,))
        row = cursor.fetchone()
        if row:
            result['name'] = row[0]
            result['aliases'] = row[1]

        cursor.execute('''
            SELECT avg_roe_10y, avg_roe_5y, roe_latest, years_count
            FROM stock_roe_summary WHERE code = ?
        ''', (code,))
        row = cursor.fetchone()
        if row:
            result['avg_roe_10y'] = round(row[0], 2) if row[0] else None
            result['avg_roe_5y'] = round(row[1], 2) if row[1] else None
            result['roe_latest'] = round(row[2], 2) if row[2] else None
            result['years_count'] = row[3]

        cursor.execute('''
            SELECT date, roe FROM roe_data
            WHERE code = ? AND date LIKE '%1231'
            ORDER BY date DESC
        ''', (code,))
        roe_history = []
        for row in cursor.fetchall():
            roe_history.append({
                'date': row[0],
                'year': row[0][:4],
                'roe': round(row[1], 2) if row[1] else None
            })
        result['roe_history'] = roe_history

        if roe_history:
            valid_roe = [r for r in roe_history if r['roe'] and 0 < r['roe'] < 100]
            if valid_roe:
                min_item = min(valid_roe, key=lambda x: x['roe'])
                result['min_roe_year'] = min_item['year']
                result['min_roe'] = min_item['roe']

        result['dividend_list'] = []

        conn.close()

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库并迁移数据"""
    # 初始化数据库和迁移数据
    init_all()
    # 初始化缓存
    init_cache_table()
    clean_expired_cache()
    print("✅ 系统启动完成")


# ========== 认证接口 ==========
@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    """用户注册"""
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    user = create_user(req.email, req.password, req.nickname or "")
    token = create_token(user['user_id'], user['email'])
    
    return TokenResponse(
        token=token,
        user={
            'user_id': user['user_id'],
            'email': user['email'],
            'nickname': user['nickname']
        }
    )

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """用户登录"""
    user = get_user_by_email(req.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    if not verify_password(req.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    update_last_login(user['user_id'])
    token = create_token(user['user_id'], user['email'])
    
    return TokenResponse(
        token=token,
        user={
            'user_id': user['user_id'],
            'email': user['email'],
            'nickname': user['nickname']
        }
    )

@app.get("/api/auth/userinfo", response_model=UserInfo)
def get_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    user = get_user_by_email(current_user['email'])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserInfo(
        user_id=user['user_id'],
        email=user['email'],
        nickname=user['nickname'],
        created_at=user['created_at']
    )

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """修改密码"""
    from auth import hash_password
    
    user = get_user_by_email(current_user['email'])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if not verify_password(req.old_password, user['password_hash']):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少6位")
    
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', 
                   (hash_password(req.new_password), user['user_id']))
    conn.commit()
    conn.close()
    
    return {"message": "密码修改成功"}

@app.post("/api/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """登出（前端删除token即可）"""
    return {"message": "已退出登录"}

# ========== 需要认证的用户数据接口 ==========
def get_portfolio_with_prices(portfolio_codes, user_id=None):
    """获取持仓列表并添加价格信息"""
    stock_codes = load_stock_codes()
    memos = load_memos(user_id)
    
    # 构建股票列表
    stocks = []
    for code in portfolio_codes:
        stock_info = stock_codes.get(code, {})
        name = stock_info.get('name', code)
        stocks.append({'name': name, 'code': code})
    
    # 批量获取股票数据
    stock_data = get_stocks_data_batch(stocks)
    
    # 构建返回结果
    portfolio_list = []
    for code in portfolio_codes:
        stock_info = stock_codes.get(code, {})
        name = stock_info.get('name', code)
        memo_info = memos.get(code, {})
        stock_data_item = stock_data.get(code, {})
        
        portfolio_list.append({
            'ticker': name,
            'code': code,
            'name': name,
            'price': stock_data_item.get('price'),
            'change': stock_data_item.get('change'),
            'change_percent': stock_data_item.get('change_percent'),
            'memo': memo_info.get('memo', ''),
            'updated_at': memo_info.get('updated_at', '')
        })
    
    return {
        "portfolio": portfolio_list,
        "count": len(portfolio_list),
        "timestamp": datetime.now().isoformat()
    }

def get_watchlist_with_prices(watchlist_codes, user_id=None):
    """获取观察列表并添加价格信息"""
    stock_codes = load_stock_codes()
    memos = load_memos(user_id)
    
    # 构建股票列表
    stocks = []
    for code in watchlist_codes:
        stock_info = stock_codes.get(code, {})
        name = stock_info.get('name', code)
        stocks.append({'name': name, 'code': code})
    
    # 批量获取股票数据
    stock_data = get_stocks_data_batch(stocks)
    
    # 构建返回结果
    watchlist_list = []
    for code in watchlist_codes:
        stock_info = stock_codes.get(code, {})
        name = stock_info.get('name', code)
        memo_info = memos.get(code, {})
        stock_data_item = stock_data.get(code, {})
        
        watchlist_list.append({
            'ticker': name,
            'code': code,
            'name': name,
            'price': stock_data_item.get('price'),
            'change': stock_data_item.get('change'),
            'change_percent': stock_data_item.get('change_percent'),
            'memo': memo_info.get('memo', ''),
            'updated_at': memo_info.get('updated_at', '')
        })
    
    return {
        "watchlist": watchlist_list,
        "count": len(watchlist_list),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/portfolio")
def get_portfolio(current_user: Optional[dict] = Depends(get_optional_user)):
    """获取持仓列表（支持登录和未登录状态）"""
    user_id = current_user['user_id'] if current_user else DEFAULT_USER_ID
    portfolio_codes = get_user_stock_list(user_id, 'portfolio')
    return get_portfolio_with_prices(portfolio_codes, user_id)

@app.get("/api/watchlist")
def get_watchlist(current_user: Optional[dict] = Depends(get_optional_user)):
    """获取观察列表（支持登录和未登录状态）"""
    user_id = current_user['user_id'] if current_user else DEFAULT_USER_ID
    watchlist_codes = get_user_stock_list(user_id, 'watchlist')
    return get_watchlist_with_prices(watchlist_codes, user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
