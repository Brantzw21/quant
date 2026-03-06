"""
动量策略模块
基于价格动量和趋势强度进行交易
"""

import numpy as np


def momentum_signal(data, params):
    """
    经典动量策略
    近期涨幅超过阈值时买入
    """
    lookback = params.get('lookback', 20)
    momentum_threshold = params.get('momentum_threshold', 0.05)  # 5%涨幅
    
    if len(data) < lookback + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    current_price = closes[-1]
    past_price = closes[-lookback]
    
    momentum = (current_price - past_price) / past_price
    
    if momentum > momentum_threshold:
        return "BUY"
    elif momentum < -momentum_threshold:
        return "SELL"
    
    return "HOLD"


def dual_momentum_signal(data, params):
    """
    双动量策略
    同时考虑短期和长期动量
    """
    short_period = params.get('short_period', 20)
    long_period = params.get('long_period', 60)
    
    if len(data) < long_period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    current_price = closes[-1]
    
    short_momentum = (current_price - closes[-short_period]) / closes[-short_period]
    long_momentum = (current_price - closes[-long_period]) / closes[-long_period]
    
    # 短期和长期都上涨 -> 买入
    if short_momentum > 0 and long_momentum > 0:
        return "BUY"
    # 短期下跌 -> 卖出
    elif short_momentum < -0.03:
        return "SELL"
    
    return "HOLD"


def trend_strength_signal(data, params):
    """
    趋势强度策略
    使用ADX指标判断趋势强度
    """
    period = params.get('period', 14)
    adx_threshold = params.get('adx_threshold', 25)
    
    if len(data) < period + 2:
        return "HOLD"
    
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    closes = [float(d["close"]) for d in data]
    
    # 计算True Range
    tr_values = []
    plus_dm = []
    minus_dm = []
    
    for i in range(1, len(highs)):
        high_diff = highs[i] - highs[i-1]
        low_diff = lows[i-1] - lows[i]
        
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_values.append(tr)
        
        if high_diff > low_diff and high_diff > 0:
            plus_dm.append(high_diff)
        else:
            plus_dm.append(0)
            
        if low_diff > high_diff and low_diff > 0:
            minus_dm.append(low_diff)
        else:
            minus_dm.append(0)
    
    if len(tr_values) < period:
        return "HOLD"
    
    # 计算ADX
    tr_sum = sum(tr_values[-period:])
    plus_dm_sum = sum(plus_dm[-period:])
    minus_dm_sum = sum(minus_dm[-period:])
    
    if tr_sum == 0:
        return "HOLD"
    
    plus_di = (plus_dm_sum / tr_sum) * 100
    minus_di = (minus_dm_sum / tr_sum) * 100
    
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    
    # 简化ADX计算
    adx = dx  # 近似值
    
    current_price = closes[-1]
    ma = sum(closes[-period:]) / period
    
    # ADX高于阈值且价格上涨 -> 上升趋势
    if adx > adx_threshold and current_price > ma:
        return "BUY"
    elif adx > adx_threshold and current_price < ma:
        return "SELL"
    
    return "HOLD"


def breakout_momentum_signal(data, params):
    """
    突破动量策略
    结合价格突破和成交量确认
    """
    lookback = params.get('lookback', 20)
    volume_ma_period = params.get('volume_ma_period', 20)
    volume_multiplier = params.get('volume_multiplier', 1.5)
    
    if len(data) < lookback + volume_ma_period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    volumes = [float(d["volume"]) for d in data]
    
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # 价格突破
    recent_high = max(highs[-lookback:-1])
    recent_low = min(lows[-lookback:-1])
    
    # 成交量确认
    avg_volume = sum(volumes[-volume_ma_period:]) / volume_ma_period
    current_volume = volumes[-1]
    
    volume_confirmed = current_volume > avg_volume * volume_multiplier
    
    # 突破高点
    if prev_price < recent_high and current_price > recent_high:
        if volume_confirmed:
            return "BUY"
    
    # 跌破低点
    if prev_price > recent_low and current_price < recent_low:
        if volume_confirmed:
            return "SELL"
    
    return "HOLD"
