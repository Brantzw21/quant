"""
布林带均值回归策略
当价格触及下轨时买入，上轨时卖出
"""

import numpy as np


def bollinger_bands_signal(data, params):
    """
    布林带均值回归策略信号
    
    参数:
    - period: 布林带周期 (默认20)
    - std_multiplier: 标准差倍数 (默认2.0)
    - oversold_pct: 超卖阈值，低于下轨多少比例买入 (默认0.98)
    - overbought_pct: 超买阈值，高于上轨多少比例卖出 (默认1.02)
    """
    period = params.get('period', 20)
    std_multiplier = params.get('std_multiplier', 2.0)
    oversold_pct = params.get('oversold_pct', 0.98)
    overbought_pct = params.get('overbought_pct', 1.02)
    
    if len(data) < period + 1:
        return "HOLD"
    
    closes = np.array([float(d["close"]) for d in data[-period:]])
    
    # 计算布林带
    ma = np.mean(closes)
    std = np.std(closes)
    upper_band = ma + std_multiplier * std
    lower_band = ma - std_multiplier * std
    
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # 买入信号：价格从下轨附近反弹
    if prev_price < lower_band * oversold_pct and current_price > lower_band:
        return "BUY"
    
    # 卖出信号：价格从上轨附近回落
    if prev_price > upper_band * overbought_pct and current_price < upper_band:
        return "SELL"
    
    return "HOLD"


def bollinger_bands_with_rsi_signal(data, params):
    """
    布林带 + RSI 组合策略
    布林带判断超卖超买，RSI确认趋势反转
    """
    period = params.get('period', 20)
    std_multiplier = params.get('std_multiplier', 2.0)
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)
    
    if len(data) < period + rsi_period + 1:
        return "HOLD"
    
    closes = np.array([float(d["close"]) for d in data[-max(period, rsi_period)-1:]])
    
    # 布林带
    ma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper_band = ma + std_multiplier * std
    lower_band = ma - std_multiplier * std
    
    # RSI
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-rsi_period:])
    avg_loss = np.mean(losses[-rsi_period:])
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # 买入：价格触及下轨 + RSI超卖
    if prev_price < lower_band and current_price > lower_band and rsi < rsi_oversold:
        return "BUY"
    
    # 卖出：价格触及上轨 + RSI超买
    if prev_price > upper_band and current_price < upper_band and rsi > rsi_overbought:
        return "SELL"
    
    return "HOLD"


def bollinger_contraction_signal(data, params):
    """
    布林带收缩策略
    当布林带收窄到一定程度，预示即将突破
    """
    period = params.get('period', 20)
    contraction_threshold = params.get('contraction_threshold', 0.03)  # 3%带宽
    breakout_mode = params.get('breakout_mode', 'up')  # up/down/both
    
    if len(data) < period + 5:
        return "HOLD"
    
    closes = np.array([float(d["close"]) for d in data[-period:]])
    highs = np.array([float(d["high"]) for d in data[-period:]])
    lows = np.array([float(d["low"]) for d in data[-period:]])
    
    ma = np.mean(closes)
    std = np.std(closes)
    
    if ma == 0:
        return "HOLD"
    
    bandwidth = (np.max(highs) - np.min(lows)) / ma
    
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # 收缩后突破
    if bandwidth < contraction_threshold:
        if breakout_mode in ['up', 'both']:
            if prev_price < ma and current_price > ma:
                return "BUY"
        if breakout_mode in ['down', 'both']:
            if prev_price > ma and current_price < ma:
                return "SELL"
    
    return "HOLD"
