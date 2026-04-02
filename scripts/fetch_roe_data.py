#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取A股股票的年末ROE数据（增量更新模式）
- 数据源：Tushare API（通过 codebuddy 代理）
- 股票列表：从SQLite数据库读取
- 增量更新：自动检测缺失年份，只更新缺失数据
"""

import os
import sqlite3
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Set, Optional

# 数据文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "finance_data.db")

# Tushare API 配置
TUSHARE_API_URL = "https://www.codebuddy.cn/v2/tool/financedata"

# 年份范围
START_YEAR = 2014
END_YEAR = 2030


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
    #              1xxxxx (深圳 ETF, 6位数)
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


def convert_code(code: str) -> str:
    """转换代码格式：sz000001 -> 000001.SZ"""
    if code.startswith('sz'):
        return f"{code[2:]}.SZ"
    elif code.startswith('sh'):
        return f"{code[2:]}.SH"
    return None


async def fetch_single_roe(code: str, name: str, start_year: int, end_year: int) -> List[Dict]:
    """
    获取单只股票的ROE数据
    """
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
    """
    批量获取股票ROE数据（逐个查询，避免API限制）

    batch_codes: [(code, name), ...]
    返回: {code: [{date, roe}, ...], ...}
    """
    if not batch_codes:
        return {}

    stock_roe = {}

    # 逐个查询（避免批量查询的数据限制）
    for code, name in batch_codes:
        roe_list = await fetch_single_roe(code, name, start_year, end_year)
        if roe_list:
            stock_roe[code] = roe_list

    return stock_roe


async def batch_fetch_roe(
    stock_list: List[tuple],
    existing_roe: Dict[str, Set[str]],
    batch_size: int = 20,
    is_full_update: bool = False
):
    """
    批量获取股票ROE数据
    - is_full_update=True: 保存所有获取到的数据
    - is_full_update=False: 增量更新，只保存新增数据
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
            # 获取批次数据
            stock_roe = await fetch_batch_roe(batch, START_YEAR, current_year)

            for code, name in batch:
                if code not in stock_roe:
                    skipped += 1
                    continue

                if is_full_update:
                    # 全量更新：保存所有获取到的数据
                    if stock_roe[code]:
                        save_roe_to_db(code, stock_roe[code])
                        success += 1
                        years = sorted([item['date'][:4] for item in stock_roe[code]])
                        print(f"  ✓ {name}: 新增 {len(stock_roe[code])} 年 ({', '.join(years)})")
                else:
                    # 增量更新：只保存新增数据
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


def main():
    """主函数"""
    print(f"\n{'='*50}")
    print(f"ROE数据增量更新脚本 (Tushare API)")
    print(f"年份范围: {START_YEAR}-{END_YEAR}")
    print(f"{'='*50}\n")

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

    # 4. 开始批量获取
    mode = "全量更新" if is_full_update else "增量更新"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取ROE数据 ({mode})...")

    success, skipped, failed = asyncio.run(
        batch_fetch_roe(stock_codes, existing_roe, is_full_update=is_full_update)
    )

    # 5. 统计结果
    print(f"\n{'='*50}")
    print(f"获取完成")
    print(f"  总股票数: {len(stock_codes)}")
    print(f"  成功更新: {success}")
    print(f"  已是最新: {skipped}")
    print(f"  失败: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
