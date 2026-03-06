"""
数据标准化模块 - 参考QUANTAXIS QAFetch
统一数据获取接口
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import json


# ==================== 标准数据格式 ====================

"""
标准K线格式:
{
    "symbol": "BTC/USDT",
    "date": "2024-01-01",
    "datetime": "2024-01-01T00:00:00",
    "open": 50000.0,
    "high": 51000.0,
    "low": 49000.0,
    "close": 50500.0,
    "volume": 1000.0,
    "amount": 50000000.0,
    "source": "binance"
}
"""


def standardize_kline(data, source: str = "unknown") -> pd.DataFrame:
    """
    标准化K线数据
    
    Args:
        data: 原始数据
        source: 数据源
    
    Returns:
        DataFrame: 标准格式
    """
    df = None
    
    # 从dict list转换
    if isinstance(data, list):
        df = pd.DataFrame(data)
    
    # 从pandas转换
    elif isinstance(data, pd.DataFrame):
        df = data.copy()
    
    if df is None or df.empty:
        return pd.DataFrame()
    
    # 标准化列名
    column_map = {
        '日期': 'date',
        'datetime': 'datetime',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        'Open': 'open',
        'Close': 'close',
        'High': 'high',
        'Low': 'low',
        'Volume': 'volume'
    }
    
    df = df.rename(columns=column_map)
    
    # 确保必需列
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            df[col] = 0
    
    # 添加source
    df['source'] = source
    
    # 时间标准化
    if 'datetime' not in df.columns and 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
    elif 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 确保数值类型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def to_ohlc(data: pd.DataFrame) -> pd.DataFrame:
    """
    转换为OHLC格式
    
    Args:
        data: 标准K线数据
    
    Returns:
        DataFrame: OHLC格式
    """
    if data.empty:
        return data
    
    df = data.copy()
    df = df.set_index('datetime')
    df = df.sort_index()
    
    return df[['open', 'high', 'low', 'close', 'volume']]


def resample_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    重采样到不同时间周期
    
    Args:
        df: OHLC数据
        timeframe: 目标周期 (1min/5min/15min/1h/4h/1d)
    
    Returns:
        DataFrame: 重采样后的数据
    """
    if df.empty or 'datetime' not in df.columns:
        return df
    
    df = df.set_index('datetime')
    
    # 映射时间周期
    rule_map = {
        '1min': '1T',
        '5min': '5T',
        '15min': '15T',
        '1h': '1H',
        '4h': '4H',
        '1d': '1D'
    }
    
    rule = rule_map.get(timeframe, '1H')
    
    resampled = df.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    return resampled.dropna()


class DataFeeder:
    """
    数据供给器
    
    参考 QUANTAXIS QAFetch 设计
    """
    
    def __init__(self):
        self.cache = {}
    
    def fetch(self, symbol: str, start: str, end: str, 
              source: str = "binance") -> pd.DataFrame:
        """
        获取数据
        
        Args:
            symbol: 交易对
            start: 开始日期
            end: 结束日期
            source: 数据源
    
        Returns:
            DataFrame: 标准格式K线
        """
        # 检查缓存
        cache_key = f"{symbol}_{source}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # TODO: 根据source获取数据
        return pd.DataFrame()
    
    def set_cache(self, symbol: str, source: str, data: pd.DataFrame):
        """设置缓存"""
        cache_key = f"{symbol}_{source}"
        self.cache[cache_key] = data


# ==================== 因子计算 ====================

def calc_returns(df: pd.DataFrame, periods: int = 1) -> pd.Series:
    """计算收益率"""
    return df['close'].pct_change(periods)


def calc_log_returns(df: pd.DataFrame) -> pd.Series:
    """计算对数收益率"""
    return np.log(df['close'] / df['close'].shift(1))


def calc_ma(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    """计算均线"""
    result = pd.DataFrame(index=df.index)
    for p in periods:
        result[f'ma{p}'] = df['close'].rolling(p).mean()
    return result


def calc_ema(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    """计算指数移动平均"""
    result = pd.DataFrame(index=df.index)
    for p in periods:
        result[f'ema{p}'] = df['close'].ewm(span=p).mean()
    return result


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算RSI"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calc_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> pd.DataFrame:
    """计算布林带"""
    ma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    
    return pd.DataFrame({
        'middle': ma,
        'upper': ma + std_dev * std,
        'lower': ma - std_dev * std
    })


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ATR"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    return atr


if __name__ == '__main__':
    # 测试
    print("数据标准化模块")
    print("使用: from data_feeder import standardize_kline, DataFeeder")
