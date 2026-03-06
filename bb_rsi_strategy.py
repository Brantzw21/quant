"""
布林带RSI组合策略
=============================
研究员: 基于布林带支撑/压力 + RSI超卖/超买双重确认

买入条件: RSI < 30 且价格触及布林下轨
卖出条件: RSI > 70 或 价格触及布林上轨
"""

import numpy as np


def bb_rsi_signal(data, params):
    """
    布林带RSI组合策略信号生成
    
    参数:
    - bb_period: 布林带周期 (默认20)
    - bb_std: 标准差倍数 (默认2.0)
    - rsi_period: RSI周期 (默认14)
    - rsi_oversold: RSI超卖阈值 (默认30)
    - rsi_overbought: RSI超买阈值 (默认70)
    - confirm_with_rsi: 是否要求RSI确认 (默认True)
    
    返回:
    - "BUY": 买入信号
    - "SELL": 卖出信号  
    - "HOLD": 持有
    """
    # 参数提取
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)
    confirm_with_rsi = params.get('confirm_with_rsi', True)
    
    # 数据不足
    max_period = max(bb_period, rsi_period) + 1
    if len(data) < max_period:
        return "HOLD"
    
    # 提取数据
    closes = np.array([float(d["close"]) for d in data])
    lows = np.array([float(d["low"]) for d in data[-bb_period-1:]])
    highs = np.array([float(d["high"]) for d in data[-bb_period-1:]])
    
    # ========== 计算布林带 ==========
    recent_closes = closes[-bb_period:]
    bb_mid = np.mean(recent_closes)           # 中轨 = N日均价
    bb_std_val = np.std(recent_closes)        # 标准差
    bb_upper = bb_mid + bb_std * bb_std_val   # 上轨
    bb_lower = bb_mid - bb_std * bb_std_val   # 下轨
    
    # ========== 计算RSI ==========
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
    
    # ========== 获取当前价和前期价 ==========
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # ========== 信号判断 ==========
    
    # 卖出信号
    if rsi > rsi_overbought:
        # RSI超买
        return "SELL"
    
    if prev_price < bb_upper and current_price > bb_upper:
        # 突破上轨
        if confirm_with_rsi and rsi < 50:
            # RSI未确认强势，谨慎卖出
            return "HOLD"
        return "SELL"
    
    # 买入信号
    if rsi < rsi_oversold:
        # RSI超卖
        return "BUY"
    
    if prev_price > bb_lower and current_price < bb_lower:
        # 跌破下轨（假突破，可能是买入机会）
        if confirm_with_rsi and rsi > 50:
            return "HOLD"
        return "BUY"
    
    # 价格触及下轨 + RSI低位
    if current_price <= bb_lower * 1.02 and rsi < 40:
        return "BUY"
    
    # 价格触及上轨 + RSI高位
    if current_price >= bb_upper * 0.98 and rsi > 60:
        return "SELL"
    
    return "HOLD"


def bb_rsi_optimized_signal(data, params):
    """
    优化版布林带RSI策略
    增加趋势过滤：只在震荡市使用
    """
    # 趋势判断
    if len(data) < 60:
        return "HOLD"
    
    closes = np.array([float(d["close"]) for d in data[-60:]])
    ma20 = np.mean( data[-60closes[-20:])
    current_price = closes[-1]
    
    # 趋势过滤
    is_uptrend = current_price > ma20
    is_downtrend = current_price < ma20
    
    # 参数
    bb_period = params.get('bb_period', 20)
    rsi_oversold = params.get('rsi_oversold', 35)  # 放宽超卖
    rsi_overbought = params.get('rsi_overbought', 65)  # 放宽超买
    
    # 简化计算
    recent_closes = closes[-bb_period:]
    bb_mid = np.mean(recent_closes)
    bb_std_val = np.std(recent_closes)
    bb_lower = bb_mid - 2.0 * bb_std_val
    bb_upper = bb_mid + 2.0 * bb_std_val
    
    # RSI
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-14:])
    avg_loss = np.mean(losses[-14:])
    
    if avg_loss == 0:
        rsi = 100
    else:
        rsi = 100 - (100 / (1 + avg_gain/avg_loss))
    
    # 信号
    if is_downtrend and rsi < rsi_oversold and current_price < bb_lower * 1.05:
        return "BUY"
    
    if is_uptrend and rsi > rsi_overbought and current_price > bb_upper * 0.95:
        return "SELL"
    
    return "HOLD"


# ===================== 测试 =====================
if __name__ == "__main__":
    # 模拟数据测试
    import random
    random.seed(42)
    
    # 生成模拟数据 (震荡市)
    data = []
    price = 100
    for i in range(100):
        price = price + random.uniform(-2, 2)
        data.append({
            "date": f"2024-01-{i+1:02d}",
            "open": price - 0.5,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000000
        })
    
    params = {
        'bb_period': 20,
        'bb_std': 2.0,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
    }
    
    signal = bb_rsi_signal(data, params)
    print(f"信号: {signal}")
    
    # 测试优化版
    signal2 = bb_rsi_optimized_signal(data, params)
    print(f"优化版信号: {signal2}")
