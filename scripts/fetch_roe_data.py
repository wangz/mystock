#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取A股股票的年末ROE数据（增量更新模式）

方案1（当前使用）: iwencai 批量查询（每次20只股票）
方案2（备用）: Tushare API（通过 codebuddy 代理，需要token）
"""

import os
import sqlite3
import time
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Set, Optional

# 强制刷新输出
sys.stdout.reconfigure(line_buffering=True)

# ========== 配置 ==========
# 当前使用的方案: 1=iwencai, 2=tushare(备用)
CURRENT_METHOD = 1

# 测试模式：限制查询数量（用于测试）
# 设置为 0 或 None 表示查询全部，设置为 100 表示只查询前100只缺失ROE的股票
TEST_LIMIT = 100

# 数据文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "finance_data.db")

# ========== 方案1: iwencai 配置 ==========
try:
    import pywencai
    IWENCAI_AVAILABLE = True
except ImportError:
    IWENCAI_AVAILABLE = False
    print("警告: pywencai 未安装，将使用备用方案")

# ========== 方案2: Tushare 配置（备用） ==========
# 当前状态: 暂不启用，因为需要token
TUSHARE_API_URL = "https://www.codebuddy.cn/v2/tool/financedata"

# 年份范围
START_YEAR = 2014
END_YEAR = 2030
BATCH_SIZE = 20  # iwencai 每次查询的股票数量


def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_FILE)


def load_stock_codes() -> List[tuple]:
    """从数据库加载A股股票代码（排除ETF），返回 [(code, name), ...]"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT code, name FROM stock_codes
        WHERE code LIKE 'sz%' OR code LIKE 'sh%'
    ''')

    all_stocks = [(row[0], row[1]) for row in cursor.fetchall()]
    conn.close()

    # 过滤掉 ETF
    # ETF 代码特征：510xxx, 511xxx, 512xxx, 513xxx, 515xxx, 588xxx (上海)
    #              1xxxxx (深圳 ETF, 6位)
    filtered = []
    for code, name in all_stocks:
        if code.startswith('sh'):
            # 上海：排除 ETF
            suffix = code[2:]
            if (suffix.startswith('5') or suffix.startswith('15') or suffix.startswith('16')):
                continue
        elif code.startswith('sz'):
            # 深圳：排除 ETF (1开头6位)
            suffix = code[2:]
            if suffix.startswith('1') and len(suffix) == 5:
                continue
        filtered.append((code, name))

    return filtered


def get_existing_roe_data() -> Dict[str, Set[str]]:
    """
    获取数据库中已有的ROE数据
    返回: {code: {date1, date2, ...}, ...}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT code, date FROM roe_data')
    roe_data = {}

    for code, date in cursor.fetchall():
        if code not in roe_data:
            roe_data[code] = set()
        roe_data[code].add(date)

    conn.close()

    return roe_data


def save_roe_to_db(code: str, roe_data: List[Dict]):
    """保存ROE数据到数据库"""
    if not roe_data:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for item in roe_data:
        if item['roe'] is not None:
            cursor.execute('''
                INSERT OR REPLACE INTO roe_data (code, date, roe)
                VALUES (?, ?, ?)
            ''', (code, item['date'], item['roe']))

    conn.commit()
    conn.close()


# ========== 方案1: iwencai 批量查询 ==========
def iwencai_query_batch(stocks: List[tuple]) -> Dict[str, Dict]:
    """
    使用 iwencai 批量查询股票ROE
    stocks: [(code, name), ...] 最多20只
    返回: {name: {code, date, roe}, ...}
    """
    if not stocks:
        return {}

    # 构建查询字符串（用换行符分隔股票名称）
    stock_names = [name.strip() for _, name in stocks]
    query = '\n'.join(stock_names) + ', ROE'

    print(f"    查询: {query[:60]}...")

    try:
        # pywencai.get 可能很慢，设置超时
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("iwencai query timeout")

        # 设置超时为120秒（iwencai 响应较慢）
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)

        try:
            result = pywencai.get(query=query, loop=True)
            signal.alarm(0)  # 取消超时
        except TimeoutError:
            print(f"    查询超时")
            return {}

        if not result:
            print(f"    无结果")
            return {}

        # 解析返回结果 - 支持两种格式
        roe_dict = {}

        for key, val in result.items():
            if not isinstance(val, pd.DataFrame) or len(val) == 0:
                continue

            df = val

            # 查找列名 - 支持多种可能的列名
            roe_col = None
            code_col = None
            name_col = None
            date_col = None

            for col in df.columns:
                col_str = str(col)
                # ROE 列
                if '净资产收益率' in col_str or 'roe' in col_str.lower():
                    if roe_col is None:
                        roe_col = col
                # 代码列
                if '代码' in col_str or 'code' in col_str.lower():
                    if code_col is None:
                        code_col = col
                # 名称列
                if '简称' in col_str or '名称' in col_str or 'name' in col_str.lower():
                    if name_col is None:
                        name_col = col
                # 日期列 - 优先 '报告期'
                if '报告期' in col_str:
                    date_col = col
                elif date_col is None and ('时间' in col_str or '区间' in col_str or 'date' in col_str.lower()):
                    date_col = col

            if not roe_col or not name_col:
                continue

            for _, row in df.iterrows():
                stock_name = str(row.get(name_col, '')).strip()
                if pd.isna(stock_name) or not stock_name:
                    continue

                stock_code = row.get(code_col, '') if code_col else ''
                roe_val = row.get(roe_col, None)

                if pd.isna(roe_val) or roe_val is None:
                    continue

                # 解析日期
                date_str = ''
                if date_col:
                    date_val = row.get(date_col, '')
                    if pd.notna(date_val):
                        date_str = parse_date_str(str(date_val))

                if stock_name and date_str:
                    # 使用返回的股票名称作为key
                    roe_dict[stock_name] = {
                        'code': stock_code,
                        'date': date_str,
                        'roe': float(roe_val)
                    }

        return roe_dict

    except Exception as e:
        print(f"    iwencai 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def parse_date_str(date_val: str) -> str:
    """
    解析日期字符串
    如: '25Q4' -> '20251231', '2025年报' -> '20251231', '20251231' -> '20251231'
    """
    date_val = str(date_val).strip()

    # 如果是纯8位日期，如 20251231
    if date_val.isdigit() and len(date_val) == 8:
        return date_val

    # 25Q4 -> 20251231
    if 'Q4' in date_val:
        year = date_val.split('Q')[0]
        if len(year) == 2:
            year = '20' + year
        return year + '1231'

    # 25Q3 -> 20250930
    if 'Q3' in date_val:
        year = date_val.split('Q')[0]
        if len(year) == 2:
            year = '20' + year
        return year + '0930'

    # 25Q2 -> 20250630
    if 'Q2' in date_val:
        year = date_val.split('Q')[0]
        if len(year) == 2:
            year = '20' + year
        return year + '0630'

    # 25Q1 -> 20250331
    if 'Q1' in date_val:
        year = date_val.split('Q')[0]
        if len(year) == 2:
            year = '20' + year
        return year + '0331'

    # 如果是纯年份，如 2025
    if date_val.isdigit() and len(date_val) == 4:
        return date_val + '1231'

    return ''


def iwencai_batch_fetch_roe(
    stock_list: List[tuple],
    existing_roe: Dict[str, Set[str]],
    batch_size: int = BATCH_SIZE,
    is_full_update: bool = False
):
    """
    使用 iwencai 批量获取股票ROE数据

    参数:
        stock_list: 股票列表 [(code, name), ...]
        existing_roe: 已有ROE数据
        batch_size: 每批查询数量，默认20
        is_full_update: 是否全量更新
    """
    total = len(stock_list)
    processed = 0
    success = 0
    skipped = 0
    failed = 0

    current_year = datetime.now().year

    for i in range(0, total, batch_size):
        batch = stock_list[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 批次 {batch_num}/{total_batches}")

        try:
            # 使用 iwencai 批量查询
            roe_results = iwencai_query_batch(batch)

            for code, name in batch:
                name_key = name.strip()

                if name_key not in roe_results:
                    skipped += 1
                    continue

                result = roe_results[name_key]
                if not result or not result.get('date'):
                    skipped += 1
                    continue

                date = result['date']
                roe_val = result['roe']

                if is_full_update:
                    # 全量更新：保存所有获取到的数据
                    save_roe_to_db(code, [{'date': date, 'roe': roe_val}])
                    success += 1
                    print(f"  ✓ {name}: {date[:4]}年 ROE={roe_val}%")
                else:
                    # 增量更新：只保存新增数据
                    existing_dates = existing_roe.get(code, set())
                    if date not in existing_dates:
                        save_roe_to_db(code, [{'date': date, 'roe': roe_val}])
                        success += 1
                        print(f"  ✓ {name}: {date[:4]}年 ROE={roe_val}%")
                    else:
                        skipped += 1

        except Exception as e:
            print(f"  ✗ 批次失败: {e}")
            failed += len(batch)

        processed += len(batch)
        print(f"  进度: {processed}/{total} | 成功: {success} | 跳过: {skipped} | 失败: {failed}")

        # 避免请求过快
        time.sleep(1)

    return success, skipped, failed


# ========== 方案2: Tushare API（备用，需要token） ==========
"""
# 以下代码暂时禁用，因为需要 codebuddy token
# 如需启用，将 CURRENT_METHOD 设为 2

import asyncio
import httpx

def convert_code(code: str) -> str:
    '''转换代码格式：sz000001 -> 000001.SZ'''
    if code.startswith('sz'):
        return f"{code[2:]}.SZ"
    elif code.startswith('sh'):
        return f"{code[2:]}.SH"
    return None


async def fetch_single_roe(code: str, name: str, start_year: int, end_year: int) -> List[Dict]:
    '''获取单只股票的ROE数据'''
    ts_code = convert_code(code)
    if not ts_code:
        return []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TUSHARE_API_URL,
                headers={'Content-Type': 'application/json'},
                json={
                    'api_name': 'fina_indicator',
                    'params': {
                        'ts_code': ts_code,
                        'start_date': f'{start_year}0101',
                        'end_date': f'{end_year}1231'
                    },
                    'fields': 'ts_code,end_date,roe_waa'
                },
                timeout=30.0
            )

            result = response.json()
            if result.get('code') != 0:
                return []

            items = result['data']['items']
    except Exception as e:
        return []

    # 筛选年末数据，并去重（同一年的数据只保留一条）
    roe_list = []
    seen_dates = set()
    for item in items:
        ts_code, date, roe_waa = item
        if not date.endswith('1231'):
            continue
        if roe_waa is None:
            continue
        # 过滤重复的年份
        year = date[:4]
        if year in seen_dates:
            continue
        seen_dates.add(year)
        roe_list.append({'date': date, 'roe': roe_waa})

    return roe_list


async def fetch_batch_roe(batch_codes: List[tuple], start_year: int, end_year: int) -> Dict[str, List[Dict]]:
    '''批量获取股票ROE数据（逐个查询，避免API限制）'''
    if not batch_codes:
        return {}

    stock_roe = {}

    # 逐个查询（避免批量查询的数据限制）
    for code, name in batch_codes:
        roe_list = await fetch_single_roe(code, name, start_year, end_year)
        if roe_list:
            stock_roe[code] = roe_list

    return stock_roe


async def tushare_batch_fetch_roe(
    stock_list: List[tuple],
    existing_roe: Dict[str, Set[str]],
    batch_size: int = 20,
    is_full_update: bool = False
):
    '''使用 Tushare API 批量获取股票ROE数据'''
    total = len(stock_list)
    processed = 0
    success = 0
    skipped = 0
    failed = 0

    current_year = datetime.now().year

    for i in range(0, total, batch_size):
        batch = stock_list[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 批次 {batch_num}/{total_batches}")

        try:
            stock_roe = await fetch_batch_roe(batch, START_YEAR, current_year)

            for code, name in batch:
                if code not in stock_roe:
                    skipped += 1
                    continue

                if is_full_update:
                    if stock_roe[code]:
                        save_roe_to_db(code, stock_roe[code])
                        success += 1
                        years = sorted([item['date'][:4] for item in stock_roe[code]])
                        print(f"  ✓ {name}: 新增 {len(stock_roe[code])} 年 ({', '.join(years)})")
                else:
                    existing_dates = existing_roe.get(code, set())
                    new_data = [item for item in stock_roe[code] if item['date'] not in existing_dates]

                    if new_data:
                        save_roe_to_db(code, new_data)
                        success += 1
                        years = sorted([item['date'][:4] for item in new_data])
                        print(f"  ✓ {name}: 新增 {len(new_data)} 年 ({', '.join(years)})")
                    else:
                        skipped += 1

        except Exception as e:
            print(f"  ✗ 批次失败: {e}")
            failed += len(batch)

        processed += len(batch)
        print(f"  进度: {processed}/{total} | 成功: {success} | 跳过: {skipped} | 失败: {failed}")

    return success, skipped, failed
"""


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"ROE数据更新脚本")
    print(f"当前方案: {'iwencai' if CURRENT_METHOD == 1 else 'Tushare (备用)'}")
    print(f"年份范围: {START_YEAR}-{END_YEAR}")
    print(f"{'='*60}\n")

    if CURRENT_METHOD == 1 and not IWENCAI_AVAILABLE:
        print("错误: iwencai 不可用，请安装 pywencai 或切换到备用方案")
        return

    # 1. 加载股票列表
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 加载股票列表...")
    stock_codes = load_stock_codes()
    print(f"  A股股票: {len(stock_codes)} 只")

    # 2. 获取已有的ROE数据
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查已有ROE数据...")
    existing_roe = get_existing_roe_data()
    print(f"  已有ROE数据: {len(existing_roe)} 只股票")

    # 判断是否全量更新
    is_full_update = len(existing_roe) == 0

    # 3. 统计缺失情况
    current_year = datetime.now().year
    target_years = set(f"{y}1231" for y in range(START_YEAR, current_year + 1))

    total_missing = 0
    stocks_with_missing = 0
    for code, _ in stock_codes:
        existing = existing_roe.get(code, set())
        missing = target_years - existing
        if missing:
            stocks_with_missing += 1
            total_missing += len(missing)

    print(f"  缺少ROE的股票: {stocks_with_missing} 只")
    print(f"  总缺失年份: {total_missing} 个\n")

    # 测试模式：筛选需要更新ROE的股票
    if TEST_LIMIT and TEST_LIMIT > 0:
        stocks_to_update = []
        for code, name in stock_codes:
            existing = existing_roe.get(code, set())
            missing = target_years - existing
            if missing:
                # 清理股票名称（去除多余空格）
                clean_name = ' '.join(name.split())
                stocks_to_update.append((code, clean_name))
                if len(stocks_to_update) >= TEST_LIMIT:
                    break
        print(f"[测试模式] 只查询前 {len(stocks_to_update)} 只缺失ROE的股票")
        print(f"  股票列表: {[name for _, name in stocks_to_update[:5]]}...\n")
        stock_codes = stocks_to_update
        is_full_update = False  # 测试模式也使用增量模式

    # 4. 开始批量获取
    mode = "全量更新" if is_full_update else "增量更新"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取ROE数据 ({mode})...")

    if CURRENT_METHOD == 1:
        # 使用 iwencai
        success, skipped, failed = iwencai_batch_fetch_roe(
            stock_codes, existing_roe, is_full_update=is_full_update
        )
    else:
        # 使用 Tushare (备用)
        print("错误: Tushare 方案暂时禁用")
        return

        # success, skipped, failed = asyncio.run(
        #     tushare_batch_fetch_roe(stock_codes, existing_roe, is_full_update=is_full_update)
        # )

    # 5. 统计结果
    print(f"\n{'='*60}")
    print(f"获取完成")
    print(f"  总股票数: {len(stock_codes)}")
    print(f"  成功更新: {success}")
    print(f"  已是最新: {skipped}")
    print(f"  失败: {failed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()