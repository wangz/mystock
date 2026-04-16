"""
测试腾讯K线数据API - 多种格式
"""

import requests
import json


def test_tencent_kline_v2():
    """测试腾讯K线数据API - 修正版"""
    
    print("=" * 60)
    print("测试腾讯K线数据API v2")
    print("=" * 60)
    
    stock_code = "sh600519"
    
    # 尝试不同的API格式
    urls_to_test = [
        # 格式1：使用fqkline接口
        ("标准K线API", f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={stock_code},day,,,10,qfq"),
        # 格式2：使用kline接口，count参数
        ("带数量参数", f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?_var=kline_dayqfq&param={stock_code},day,,,10,qfq&count=10"),
        # 格式3：使用新版API
        ("新版API", f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?_var=kline_dayqfq&param={stock_code},day,,,10,qfq&_r=0.123"),
        # 格式4：腾讯股票历史K线
        ("历史K线", f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?_var=kline_dayqfq&param={stock_code},day,,,10,qfq"),
    ]
    
    for name, url in urls_to_test:
        print(f"\n测试 {name}...")
        print(f"  URL: {url[:100]}...")
        try:
            response = requests.get(url, timeout=5)
            print(f"  状态码: {response.status_code}")
            text = response.text
            print(f"  响应: {text[:300]}")
            
            if 'bad params' not in text and len(text) > 100:
                # 尝试解析
                if '=' in text:
                    data_str = text.split('=', 1)[1]
                    try:
                        data = json.loads(data_str)
                        print(f"  ✅ JSON解析成功")
                        print(f"  数据预览: {json.dumps(data, indent=2)[:800]}")
                    except:
                        pass
                        
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    
    print("\n" + "=" * 60)


def test_baostock_kline():
    """测试baostock K线数据"""
    
    print("\n\n测试 BaoStock K线数据...")
    print("=" * 60)
    
    try:
        import baostock as bs
        import pandas as pd
        
        # 登录
        lg = bs.login()
        print(f"登录状态: {lg.error_msg}")
        
        # 获取日K线数据
        rs = bs.query_history_k_data_plus(
            "sh.600519",
            "date,code,open,high,low,close,volume",
            start_date='2026-01-01',
            end_date='2026-04-16',
            frequency="d",
            adjustflag="2"  # 前复权
        )
        
        print(f"\n数据获取状态: {rs.error_code} - {rs.error_msg}")
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        
        print(f"获取到 {len(data_list)} 条数据")
        if data_list:
            print(f"最新数据: {data_list[-1]}")
            print(f"前5条数据: ")
            for row in data_list[:5]:
                print(f"  {row}")
        
        # 登出
        bs.logout()
        
        return len(data_list) > 0
        
    except ImportError:
        print("❌ BaoStock未安装")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def test_akshare_kline():
    """测试akshare K线数据"""
    
    print("\n\n测试 akshare K线数据...")
    print("=" * 60)
    
    try:
        import akshare as ak
        
        # 获取股票历史K线
        df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20260101", end_date="20260416", adjust="qfq")
        
        print(f"✅ 获取成功！数据形状: {df.shape}")
        print(f"\n列名: {df.columns.tolist()}")
        print(f"\n前5行数据:")
        print(df.head())
        print(f"\n数据统计:")
        print(df.describe())
        
        # 转换为ECharts格式
        print(f"\n转换为ECharts格式:")
        for idx, row in df.tail(3).iterrows():
            print(f"  日期: {row['日期']}, 开: {row['开盘']}, 收: {row['收盘']}, 高: {row['最高']}, 低: {row['最低']}, 量: {row['成交量']}")
        
        return True
        
    except ImportError:
        print("❌ akshare未安装")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n开始测试各种K线数据源...\n")
    
    # 测试腾讯API
    test_tencent_kline_v2()
    
    # 测试BaoStock
    bao_success = test_baostock_kline()
    
    # 测试akshare
    ak_success = test_akshare_kline()
    
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print("=" * 60)
    print(f"腾讯API: ❌ (API已失效或需要新格式)")
    print(f"BaoStock: {'✅' if bao_success else '❌'}")
    print(f"akshare: {'✅' if ak_success else '❌'}")
    print("=" * 60)
