#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算并存储股票ROE汇总数据
- avg_roe_10y: 近10年平均ROE
- avg_roe_5y: 近5年平均ROE
- roe_latest: 最新ROE
"""

import sqlite3
from datetime import datetime

DB_FILE = "/Users/wz/Documents/trae_projects/ai-stock/finance_data.db"


def get_db_connection():
    return sqlite3.connect(DB_FILE)


def create_table():
    """创建汇总表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_roe_summary (
            code VARCHAR(10) PRIMARY KEY,
            avg_roe_10y DECIMAL(8,4),
            avg_roe_5y DECIMAL(8,4),
            roe_latest DECIMAL(8,4),
            years_count INTEGER,
            update_date VARCHAR(10)
        )
    ''')

    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_avg_roe_10y 
        ON stock_roe_summary(avg_roe_10y DESC)
    ''')

    conn.commit()
    conn.close()
    print("✓ 表创建完成")


def calculate_roe_summary():
    """计算所有股票的ROE汇总数据（过滤异常值）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 从 roe_data 表获取所有股票代码
    cursor.execute('''
        SELECT DISTINCT code FROM roe_data 
        WHERE date LIKE '%1231'
        ORDER BY code
    ''')
    codes = [row[0] for row in cursor.fetchall()]
    print(f"找到 {len(codes)} 只股票有年末ROE数据")

    # 过滤条件：ROE 在合理范围内 (-50% ~ 150%)
    # 超过这个范围的通常是公司重组等特殊情况，不参与平均计算
    ROE_MIN = -50
    ROE_MAX = 150

    print(f"ROE 过滤范围: {ROE_MIN}% ~ {ROE_MAX}%")

    # 计算每只股票的汇总数据
    results = []
    for code in codes:
        # 近10年平均 ROE (2015-2024)，过滤异常值
        cursor.execute('''
            SELECT roe FROM roe_data
            WHERE code = ?
            AND date LIKE '%1231'
            AND date >= '20151231'
            AND date <= '20241231'
            AND roe IS NOT NULL
            AND roe > ? AND roe < ?
        ''', (code, ROE_MIN, ROE_MAX))
        roe_list_10y = [row[0] for row in cursor.fetchall()]
        avg_10y = sum(roe_list_10y) / len(roe_list_10y) if roe_list_10y else None
        count_10y = len(roe_list_10y)

        # 近5年平均 ROE (2020-2024)，过滤异常值
        cursor.execute('''
            SELECT roe FROM roe_data
            WHERE code = ?
            AND date LIKE '%1231'
            AND date >= '20200101'
            AND date <= '20241231'
            AND roe IS NOT NULL
            AND roe > ? AND roe < ?
        ''', (code, ROE_MIN, ROE_MAX))
        roe_list_5y = [row[0] for row in cursor.fetchall()]
        avg_5y = sum(roe_list_5y) / len(roe_list_5y) if roe_list_5y else None

        # 最新 ROE (最近的年末，不过滤)
        cursor.execute('''
            SELECT roe FROM roe_data
            WHERE code = ?
            AND date LIKE '%1231'
            ORDER BY date DESC
            LIMIT 1
        ''', (code,))
        row = cursor.fetchone()
        roe_latest = row[0] if row else None

        results.append({
            'code': code,
            'avg_roe_10y': avg_10y,
            'avg_roe_5y': avg_5y,
            'roe_latest': roe_latest,
            'years_count': count_10y if count_10y else 0
        })

    conn.close()
    return results


def save_to_db(results):
    """保存到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    for r in results:
        cursor.execute('''
            INSERT OR REPLACE INTO stock_roe_summary 
            (code, avg_roe_10y, avg_roe_5y, roe_latest, years_count, update_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            r['code'],
            r['avg_roe_10y'],
            r['avg_roe_5y'],
            r['roe_latest'],
            r['years_count'],
            today
        ))

    conn.commit()
    conn.close()
    print(f"✓ 保存 {len(results)} 条记录")


def show_sample():
    """显示样本数据"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n样本数据:")
    cursor.execute('''
        SELECT s.code, c.name, s.avg_roe_10y, s.avg_roe_5y, s.roe_latest, s.years_count
        FROM stock_roe_summary s
        LEFT JOIN stock_codes c ON s.code = c.code
        ORDER BY s.avg_roe_10y DESC
        LIMIT 10
    ''')

    print("-" * 70)
    print(f"{'代码':<12} {'名称':<10} {'10年平均':<10} {'5年平均':<10} {'最新ROE':<10} {'年份数'}")
    print("-" * 70)

    for row in cursor.fetchall():
        code, name, avg_10y, avg_5y, roe_latest, years_count = row
        name = name or '-'
        avg_10y = f"{avg_10y:.2f}%" if avg_10y else "-"
        avg_5y = f"{avg_5y:.2f}%" if avg_5y else "-"
        roe_latest = f"{roe_latest:.2f}%" if roe_latest else "-"
        print(f"{code:<12} {name:<10} {avg_10y:<10} {avg_5y:<10} {roe_latest:<10} {years_count}")

    conn.close()


def main():
    print(f"\n{'='*50}")
    print(f"ROE汇总数据计算")
    print(f"{'='*50}\n")

    # 1. 创建表
    print("[1/3] 创建表...")
    create_table()

    # 2. 计算汇总数据
    print("[2/3] 计算汇总数据...")
    results = calculate_roe_summary()
    print(f"  计算完成: {len(results)} 只股票")

    # 3. 保存到数据库
    print("[3/3] 保存数据...")
    save_to_db(results)

    # 4. 显示样本
    print("\n[4/4] 样本数据:")
    show_sample()

    print(f"\n{'='*50}")
    print("完成！")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
