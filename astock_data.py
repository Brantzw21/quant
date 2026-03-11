#!/usr/bin/env python3
"""
A股数据管理器
支持 Baostock / Tushare / Akshare 多数据源
"""

import sys
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

# 尝试导入各数据源
try:
    import baostock as bs
    HAS_BAOSTOCK = True
except ImportError:
    HAS_BAOSTOCK = False

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False


class AStockDataManager:
    """
    A股数据管理器
    
    支持:
    - 实时行情
    - 历史K线
    - 指数数据
    - 财务数据
    """
    
    def __init__(self, source: str = "baostock", token: str = ""):
        """
        初始化
        
        Args:
            source: 数据源 ('baostock', 'tushare', 'akshare')
            token: Tushare token (仅tushare需要)
        """
        self.source = source
        self.token = token
        self.connected = False
        
        self._connect()
    
    def _connect(self):
        """连接数据源"""
        if self.source == "baostock":
            self._connect_baostock()
        elif self.source == "tushare":
            self._connect_tushare()
        elif self.source == "akshare":
            self._connect_akshare()
        else:
            print(f"❌ 不支持的数据源: {self.source}")
    
    def _connect_baostock(self):
        """连接Baostock"""
        if not HAS_BAOSTOCK:
            print("❌ baostock 未安装: pip install baostock")
            return
        
        try:
            lg = bs.login()
            if lg.error_code == '0':
                self.connected = True
                print("✅ 已连接 Baostock")
            else:
                print(f"❌ Baostock连接失败: {lg.error_msg}")
        except Exception as e:
            print(f"❌ Baostock连接失败: {e}")
    
    def _connect_tushare(self):
        """连接Tushare"""
        if not HAS_TUSHARE:
            print("❌ tushare 未安装: pip install tushare")
            return
        
        try:
            if self.token:
                ts.set_token(self.token)
            self.pro = ts.pro_api()
            self.connected = True
            print("✅ 已连接 Tushare")
        except Exception as e:
            print(f"❌ Tushare连接失败: {e}")
    
    def _connect_akshare(self):
        """连接Akshare"""
        if not HAS_AKSHARE:
            print("❌ akshare 未安装: pip install akshare")
            return
        
        self.connected = True
        print("✅ 已连接 Akshare (无需登录)")
    
    def disconnect(self):
        """断开连接"""
        if self.source == "baostock" and HAS_BAOSTOCK:
            bs.logout()
            self.connected = False
            print("✅ 已断开 Baostock")
    
    def get_kline(self, symbol: str, start_date: str = "", 
                  end_date: str = "", freq: str = "d") -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码 (e.g., 'sh.600000' 或 'sz.000001')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            freq: 频率 ('d'=日, 'w'=周, 'm'=月)
        
        Returns:
            DataFrame
        """
        if not self.connected:
            return pd.DataFrame()
        
        # 默认日期
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        if self.source == "baostock":
            return self._get_kline_baostock(symbol, start_date, end_date, freq)
        elif self.source == "akshare":
            return self._get_kline_akshare(symbol, start_date, end_date)
        
        return pd.DataFrame()
    
    def _get_kline_baostock(self, symbol: str, start_date: str, 
                           end_date: str, freq: str) -> pd.DataFrame:
        """Baostock获取K线"""
        # 字段映射
        field_map = {
            'd': 'date,code,open,high,low,close,volume,amount,turn',
            'w': 'date,code,open,high,low,close,volume',
            'm': 'date,code,open,high,low,close,volume'
        }
        
        fields = field_map.get(freq, field_map['d'])
        
        rs = bs.query_history_k_data_plus(
            symbol,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency=freq
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list, columns=rs.fields.split(','))
        
        # 转换数值列
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _get_kline_akshare(self, symbol: str, start_date: str, 
                          end_date: str) -> pd.DataFrame:
        """Akshare获取K线"""
        # 转换代码格式
        code = symbol.split('.')[-1]
        exchange = symbol.split('.')[0]
        
        if exchange == 'sh':
            code = f"sh{code}"
        else:
            code = f"sz{code}"
        
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                   start_date=start_date.replace('-', ''),
                                   end_date=end_date.replace('-', ''))
            df = df.rename(columns={
                '日期': 'date',
                '股票代码': 'code',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'turn',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            return df
        except Exception as e:
            print(f"❌ Akshare获取失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, symbols: List[str]) -> List[Dict]:
        """
        获取实时行情
        
        Args:
            symbols: 股票代码列表
        
        Returns:
            行情列表
        """
        if not self.connected:
            return []
        
        if self.source == "akshare" and HAS_AKSHARE:
            return self._get_realtime_akshare(symbols)
        
        # 其他数据源暂不支持实时行情
        return []
    
    def _get_realtime_akshare(self, symbols: List[str]) -> List[Dict]:
        """Akshare获取实时行情"""
        results = []
        
        for symbol in symbols:
            try:
                code = symbol.split('.')[-1]
                df = ak.stock_zh_a_spot_em()
                
                row = df[df['代码'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    results.append({
                        'symbol': symbol,
                        'name': r.get('名称', ''),
                        'price': float(r.get('最新价', 0)),
                        'change': float(r.get('涨跌幅', 0)),
                        'volume': float(r.get('成交量', 0)),
                        'amount': float(r.get('成交额', 0)),
                        'high': float(r.get('最高', 0)),
                        'low': float(r.get('最低', 0)),
                        'open': float(r.get('今开', 0)),
                        'prev_close': float(r.get('昨收', 0)),
                    })
            except Exception as e:
                print(f"获取 {symbol} 行情失败: {e}")
        
        return results
    
    def get_index_components(self, index_code: str = "sh.000300") -> List[Dict]:
        """
        获取指数成分股
        
        Args:
            index_code: 指数代码 (sh.000300=沪深300)
        
        Returns:
            成分股列表
        """
        if self.source == "baostock" and HAS_BAOSTOCK:
            rs = bs.query_hs300_stocks()
            
            stocks = []
            while (rs.error_code == '0') & rs.next():
                stocks.append(rs.get_row_data())
            
            if stocks:
                df = pd.DataFrame(stocks, columns=rs.fields.split(','))
                return df.to_dict('records')
        
        return []
    
    def get_fundamental(self, symbol: str) -> Dict:
        """
        获取基本面数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            基本面数据
        """
        if self.source == "akshare" and HAS_AKSHARE:
            try:
                code = symbol.split('.')[-1]
                df = ak.stock_individual_info_em(symbol=code)
                
                info = {}
                for _, row in df.iterrows():
                    info[row['item']] = row['value']
                
                return info
            except Exception as e:
                print(f"获取基本面失败: {e}")
        
        return {}


# ==================== 常用指数 ====================

INDEX_CODES = {
    # 主要指数
    "sh.000001": "上证指数",
    "sh.000300": "沪深300",
    "sh.000016": "上证50",
    "sh.000905": "中证500",
    "sz.399001": "深证成指",
    "sz.399006": "创业板指",
    "sz.399300": "创业板50",
    
    # 行业指数
    "sh.000688": "科创50",
    "sz.399852": "中证1000",
}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("A股数据管理器测试")
    print("=" * 50)
    
    # 创建管理器 (使用baostock)
    dm = AStockDataManager(source="baostock")
    
    # 获取K线
    print("\n获取上证指数K线...")
    df = dm.get_kline("sh.000001", start_date="2026-01-01")
    print(f"获取到 {len(df)} 条数据")
    if not df.empty:
        print(df.tail())
    
    # 获取实时行情
    print("\n获取实时行情...")
    quotes = dm.get_realtime_quote(["sh.600000", "sz.000001"])
    for q in quotes:
        print(f"  {q.get('symbol')}: {q.get('price')}")
    
    # 断开
    dm.disconnect()
