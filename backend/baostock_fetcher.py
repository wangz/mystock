"""
BaoStock价格获取模块（精简版）
只用于分红计算中的历史价格获取
"""

import baostock as bs
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaoStockPriceFetcher:
    """BaoStock价格获取器，专用于分红计算"""
    
    @staticmethod
    def convert_code(symbol: str) -> str:
        """将股票代码转换为BaoStock格式"""
        if symbol.startswith('6'):
            return f"sh.{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz.{symbol}"
        else:
            return f"sz.{symbol}"
    
    @staticmethod
    def login():
        """登录BaoStock系统"""
        try:
            lg = bs.login()
            if lg.error_code == '0':
                logger.info("BaoStock登录成功")
                return lg
            else:
                logger.error(f"BaoStock登录失败: {lg.error_msg}")
                return None
        except Exception as e:
            logger.error(f"BaoStock登录异常: {e}")
            return None
    
    @staticmethod
    def logout():
        """登出BaoStock系统"""
        try:
            bs.logout()
            logger.info("BaoStock已登出")
        except Exception as e:
            logger.warning(f"BaoStock登出异常: {e}")
    
    @staticmethod
    def batch_get_prices(symbol: str, date_list: List[str]) -> Dict[str, float]:
        """
        批量获取多个日期的收盘价（分红计算专用）
        
        Args:
            symbol: 股票代码
            date_list: 日期字符串列表，格式 'YYYYMMDD'
            
        Returns:
            字典 {日期: 价格}
        """
        if not date_list:
            return {}
        
        # 预处理日期
        valid_dates = []
        date_objects = []
        
        for date_str in date_list:
            if date_str and len(date_str) >= 8:
                clean_date = date_str.replace('/', '').replace('-', '')
                if len(clean_date) == 8:
                    valid_dates.append(clean_date)
                    
                    # 转换为datetime对象用于范围查询
                    date_obj = datetime.strptime(clean_date, '%Y%m%d')
                    date_objects.append(date_obj)
        
        if not valid_dates:
            return {}
        
        # 确定查询范围
        min_date = min(date_objects)
        max_date = max(date_objects)
        
        # 扩展范围确保覆盖所有日期（前后扩展10天）
        query_start = (min_date - timedelta(days=10)).strftime('%Y-%m-%d')
        query_end = (max_date + timedelta(days=10)).strftime('%Y-%m-%d')
        
        lg = BaoStockPriceFetcher.login()
        if not lg:
            logger.error("无法登录BaoStock，返回空结果")
            return {}
        
        try:
            code = BaoStockPriceFetcher.convert_code(symbol)
            
            logger.info(f"使用BaoStock获取 {symbol} 价格: {len(valid_dates)} 个日期")
            
            # 获取时间段内的所有数据（前复权）
            rs = bs.query_history_k_data_plus(
                code,
                "date,close",
                start_date=query_start,
                end_date=query_end,
                frequency="d",
                adjustflag="2"  # 前复权
            )
            
            all_data = []
            while (rs.error_code == '0') & rs.next():
                all_data.append(rs.get_row_data())
            
            if len(all_data) == 0:
                logger.warning(f"{symbol} 在时间段内无数据")
                return {}
            
            # 构建完整的日期-价格映射
            full_price_map = {}
            for row in all_data:
                date_key = row[0].replace('-', '')
                price = float(row[1]) if row[1] else None
                if price is not None:
                    full_price_map[date_key] = price
            
            # 筛选我们需要的日期
            result = {}
            missing_dates = []
            
            for target_date in valid_dates:
                if target_date in full_price_map:
                    result[target_date] = full_price_map[target_date]
                else:
                    # 不是交易日，找最接近的交易日（5天内）
                    target_dt = datetime.strptime(target_date, '%Y%m%d')
                    closest_diff = float('inf')
                    closest_price = None
                    
                    for date_key, price in full_price_map.items():
                        try:
                            row_dt = datetime.strptime(date_key, '%Y%m%d')
                            diff = abs((row_dt - target_dt).days)
                            
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_price = price
                        except:
                            continue
                    
                    if closest_price is not None and closest_diff <= 5:
                        result[target_date] = closest_price
                        logger.debug(f"{symbol} {target_date} 使用最近交易日价格")
                    else:
                        missing_dates.append(target_date)
            
            if missing_dates:
                logger.warning(f"{symbol} 有 {len(missing_dates)} 个日期未找到价格数据")
            
            logger.info(f"BaoStock获取完成: {symbol} 成功 {len(result)}/{len(valid_dates)} 个日期")
            
            return result
        
        except Exception as e:
            logger.error(f"BaoStock批量获取失败 {symbol}: {e}")
        
        finally:
            BaoStockPriceFetcher.logout()
        
        return {}
    
    @staticmethod
    def get_stock_price(symbol: str, date_str: str) -> Optional[float]:
        """
        获取指定日期的收盘价
        
        Args:
            symbol: 股票代码
            date_str: 日期字符串，格式 'YYYY-MM-DD' 或 'YYYYMMDD'
            
        Returns:
            收盘价（浮点数），如果未找到则返回None
        """
        if not date_str or len(date_str) < 8:
            return None
        
        # 统一日期格式为 YYYYMMDD
        clean_date = date_str.replace('/', '').replace('-', '')
        if len(clean_date) != 8:
            return None
        
        # 使用批量获取方式
        price_map = BaoStockPriceFetcher.batch_get_prices(symbol, [clean_date])
        if clean_date in price_map:
            return price_map[clean_date]
        
        return None

# 兼容旧代码的函数
def batch_get_prices(symbol: str, dates: List[str]) -> Dict[str, float]:
    """批量获取价格的兼容函数"""
    return BaoStockPriceFetcher.batch_get_prices(symbol, dates)

def get_stock_price(symbol: str, date_str: str) -> Optional[float]:
    """获取单个日期的兼容函数"""
    return BaoStockPriceFetcher.get_stock_price(symbol, date_str)

# 测试函数
if __name__ == "__main__":
    print("测试BaoStock价格获取（分红计算专用）")
    print("="*60)
    
    # 测试批量获取
    test_dates = ["20240627", "20230630", "20220606", "20210625", "20200623"]
    price_map = batch_get_prices("600519", test_dates)
    
    print(f"批量获取贵州茅台 ({len(test_dates)} 个日期):")
    for date, price in price_map.items():
        print(f"  {date}: ¥{price:.2f}")
    
    print(f"成功获取 {len(price_map)}/{len(test_dates)} 个日期")
    
    # 测试单个日期
    price = get_stock_price("600519", "20200623")
    print(f"\n单个日期获取 20200623: ¥{price:.2f}")