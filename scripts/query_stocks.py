#!/usr/bin/env python3
import pywencai

query = 'PE<6,股息率>4'
print(f'查询条件：PE<6 且 股息率>4%')
print('=' * 80)

df = pywencai.get(query=query, loop=True, max_retries=2)

if df is not None and not df.empty:
    print(f'✅ 共找到 {len(df)} 只股票')
    print()
    
    print(f"{'股票代码':<12} {'股票简称':<10} {'最新价':>8} {'市盈率(PE)':>10} {'股息率(%)':>10} {'总市值':>12}")
    print('-' * 80)
    
    for _, row in df.iterrows():
        code = row.get('股票代码', 'N/A')
        name = row.get('股票简称', 'N/A')
        price = row.get('最新价', 'N/A')
        pe = row.get('市盈率(pe)[20260327]', 'N/A')
        dividend = row.get('股息率(近12个月)[20260327]', 'N/A')
        market_cap = row.get('总市值[20260327]', 'N/A')
        
        print(f"{code:<12} {name:<10} {str(price):>8} {str(pe):>10} {str(dividend):>10} {str(market_cap):>12}")
else:
    print('❌ 查询结果为空')
