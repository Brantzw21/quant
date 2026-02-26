"""
技术指标库 - Technical Indicators
=====================================

收集了开源项目中常见的技术指标:
- 趋势指标
- 动量指标
- 波动率指标
- 成交量指标

参考: finta, pandas_talib, pyti

作者: AI量化系统
"""

import numpy as np
import pandas as pd
from typing import Union, List


def EMA(data: Union[pd.Series, List], period: int) -> float:
    """指数移动平均"""
    if isinstance(data, list):
        data = pd.Series(data)
    return data.ewm(span=period, adjust=False).mean().iloc[-1]


def SMA(data: Union[pd.Series, List], period: int) -> float:
    """简单移动平均"""
    if isinstance(data, list):
        data = pd.Series(data)
    return data.rolling(window=period).mean().iloc[-1]


def RSI(data: Union[pd.Series, List], period: int = 14) -> float:
    """RSI指标"""
    if isinstance(data, list):
        data = pd.Series(data)
    
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if hasattr(rsi, 'iloc') else rsi


def MACD(data: Union[pd.Series, List], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD指标
    
    Returns:
        macd: 快线
        signal: 信号线
        histogram: 柱状图
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    
    return {
        'macd': macd.iloc[-1],
        'signal': signal_line.iloc[-1],
        'histogram': histogram.iloc[-1]
    }


def BOLL(data: Union[pd.Series, List], period: int = 20, std_dev: float = 2.0) -> dict:
    """
    布林带
    
    Returns:
        upper: 上轨
        middle: 中轨
        lower: 下轨
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        'upper': upper.iloc[-1],
        'middle': middle.iloc[-1],
        'lower': lower.iloc[-1]
    }


def ATR(high: Union[pd.Series, List], 
       low: Union[pd.Series, List], 
       close: Union[pd.Series, List], 
       period: int = 14) -> float:
    """
    ATR - 平均真实波幅
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1]


def ADX(high: Union[pd.Series, List],
        low: Union[pd.Series, List],
        close: Union[pd.Series, List],
        period: int = 14) -> dict:
    """
    ADX - 平均趋向指数
    
    Returns:
        adx: ADX值
        plus_di: +DI
        minus_di: -DI
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Smoothed
    tr_smooth = tr.rolling(window=period).mean()
    plus_dm_smooth = plus_dm.rolling(window=period).mean()
    minus_dm_smooth = minus_dm.rolling(window=period).mean()
    
    # DI
    plus_di = (plus_dm_smooth / tr_smooth) * 100
    minus_di = (minus_dm_smooth / tr_smooth) * 100
    
    # DX
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    
    # ADX
    adx = dx.rolling(window=period).mean()
    
    return {
        'adx': adx.iloc[-1],
        'plus_di': plus_di.iloc[-1],
        'minus_di': minus_di.iloc[-1]
    }


def Stochastic(high: Union[pd.Series, List],
               low: Union[pd.Series, List],
               close: Union[pd.Series, List],
               period: int = 14,
               smooth_k: int = 3,
               smooth_d: int = 3) -> dict:
    """
    Stochastic - 随机指标
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    k_smooth = k.rolling(window=smooth_k).mean()
    d = k_smooth.rolling(window=smooth_d).mean()
    
    return {
        'k': k.iloc[-1],
        'd': d.iloc[-1]
    }


def VWAP(high: Union[pd.Series, List],
        low: Union[pd.Series, List],
        close: Union[pd.Series, List],
        volume: Union[pd.Series, List]) -> float:
    """
    VWAP - 成交量加权平均价
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap.iloc[-1]


def OBV(close: Union[pd.Series, List], 
        volume: Union[pd.Series, List]) -> float:
    """
    OBV - 能量潮
    """
    if isinstance(close, list):
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    obv = (np.sign(close.diff()) * volume).cumsum()
    
    return obv.iloc[-1]


def Williams_R(high: Union[pd.Series, List],
              low: Union[pd.Series, List],
              close: Union[pd.Series, List],
              period: int = 14) -> float:
    """
    Williams %R - 威廉指标
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    wr = -100 * (highest_high - close) / (highest_high - lowest_low)
    
    return wr.iloc[-1]


def CCI(high: Union[pd.Series, List],
        low: Union[pd.Series, List],
        close: Union[pd.Series, List],
        period: int = 20) -> float:
    """
    CCI - 商品通道指数
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    tp = (high + low + close) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    cci = (tp - sma) / (0.015 * mad)
    
    return cci.iloc[-1]


def ROC(data: Union[pd.Series, List], period: int = 12) -> float:
    """
    ROC - 变动率指标
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    roc = ((data - data.shift(period)) / data.shift(period)) * 100
    
    return roc.iloc[-1]


def MFI(high: Union[pd.Series, List],
        low: Union[pd.Series, List],
        close: Union[pd.Series, List],
        volume: Union[pd.Series, List],
        period: int = 14) -> float:
    """
    MFI - 资金流量指标
    """
    if isinstance(high, list):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    tp = (high + low + close) / 3
    raw_money_flow = tp * volume
    
    positive_flow = raw_money_flow.where(tp > tp.shift(1), 0)
    negative_flow = raw_money_flow.where(tp < tp.shift(1), 0)
    
    money_ratio = positive_flow.rolling(window=period).sum() / \
                  negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + money_ratio))
    
    return mfi.iloc[-1]


# ==================== 信号生成 ====================

def generate_signals(closes: List[float], 
                   highs: List[float] = None,
                   lows: List[float] = None,
                   volumes: List[float] = None) -> dict:
    """
    综合信号生成
    
    Returns:
        各指标信号
    """
    result = {}
    
    if len(closes) < 30:
        return result
    
    # 转为Series
    close = pd.Series(closes)
    high = pd.Series(highs) if highs else close
    low = pd.Series(lows) if lows else close
    volume = pd.Series(volumes) if volumes else pd.Series([1]*len(closes))
    
    # RSI
    result['rsi'] = RSI(close, 14)
    
    # MACD
    result['macd'] = MACD(close)
    
    # 布林带
    result['boll'] = BOLL(close, 20, 2.0)
    
    # ATR
    if highs and lows:
        result['atr'] = ATR(high, low, close, 14)
    
    # ADX
    if highs and lows:
        result['adx'] = ADX(high, low, close, 14)
    
    # Stochastic
    if highs and lows:
        result['stoch'] = Stochastic(high, low, close, 14)
    
    # OBV
    if volumes:
        result['obv'] = OBV(close, volume)
    
    return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 模拟数据
    closes = [100 + random.uniform(-5, 5) for _ in range(100)]
    highs = [c + random.uniform(0, 3) for c in closes]
    lows = [c - random.uniform(0, 3) for c in closes]
    volumes = [random.randint(1000000, 5000000) for _ in range(100)]
    
    # 计算指标
    print("RSI:", RSI(closes, 14))
    print("MACD:", MACD(closes))
    print("BOLL:", BOLL(closes, 20, 2.0))
    print("ATR:", ATR(highs, lows, closes, 14))
    print("ADX:", ADX(highs, lows, closes, 14))
    print("Stochastic:", Stochastic(highs, lows, closes, 14))
    print("OBV:", OBV(closes, volumes))
