"""
高级策略库 - Advanced Strategies
================================

整合了多个开源项目的优秀策略:
- 海龟交易法则
- 双均线交叉
- 布林带回归
- 通道突破
- 动量策略

作者: AI量化系统
"""

import numpy as np
import pandas as pd
from typing import List, Dict


# ==================== 海龟交易法则 ====================

def turtle_signal(data: List[Dict], params: Dict) -> str:
    """
    海龟交易法则
    
    原理:
    - 突破20日高点买入
    - 跌破10日低点卖出
    
    参数:
    - entry_period: 入场周期 (默认20)
    - exit_period: 出场周期 (默认10)
    """
    entry_period = params.get('entry_period', 20)
    exit_period = params.get('exit_period', 10)
    
    if len(data) < entry_period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    
    # 20日高点
    entry_high = max(highs[-entry_period:-1])
    # 10日低点
    exit_low = min(lows[-exit_period:-1])
    
    current_price = closes[-1]
    prev_price = closes[-2]
    
    # 买入: 突破20日高点
    if prev_price <= entry_high and current_price > entry_high:
        return "BUY"
    
    # 卖出: 跌破10日低点
    if prev_price >= exit_low and current_price < exit_low:
        return "SELL"
    
    return "HOLD"


# ==================== 双均线交叉 ====================

def ma_cross_signal(data: List[Dict], params: Dict) -> str:
    """
    均线交叉策略
    
    参数:
    - fast: 快线周期 (默认10)
    - slow: 慢线周期 (默认50)
    """
    fast = params.get('fast', 10)
    slow = params.get('slow', 50)
    
    if len(data) < slow + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    # 简单均线
    ma_fast = np.mean(closes[-fast:])
    ma_slow = np.mean(closes[-slow:])
    
    ma_fast_prev = np.mean(closes[-fast-1:-1])
    ma_slow_prev = np.mean(closes[-slow-1:-1])
    
    # 金叉
    if ma_fast_prev <= ma_slow_prev and ma_fast > ma_slow:
        return "BUY"
    
    # 死叉
    if ma_fast_prev >= ma_slow_prev and ma_fast < ma_slow:
        return "SELL"
    
    return "HOLD"


# ==================== 布林带回归 ====================

def bollinger_reversion_signal(data: List[Dict], params: Dict) -> str:
    """
    布林带均值回归策略
    
    原理:
    - 价格触及下轨买入
    - 价格触及上轨卖出
    """
    period = params.get('period', 20)
    std_dev = params.get('std_dev', 2.0)
    
    if len(data) < period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    ma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    
    current = closes[-1]
    
    # 买入: 触及下轨
    if current < lower:
        return "BUY"
    
    # 卖出: 触及上轨
    if current > upper:
        return "SELL"
    
    return "HOLD"


# ==================== 动量策略 ====================

def momentum_signal(data: List[Dict], params: Dict) -> str:
    """
    动量策略
    
    原理:
    - 过去N天上涨 -> 买入
    - 过去N天下跌 -> 卖出
    """
    lookback = params.get('lookback', 20)
    threshold = params.get('threshold', 0.05)
    
    if len(data) < lookback + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    momentum = (closes[-1] - closes[-lookback]) / closes[-lookback]
    
    # 上涨超过阈值
    if momentum > threshold:
        return "BUY"
    
    # 下跌超过阈值
    if momentum < -threshold:
        return "SELL"
    
    return "HOLD"


# ==================== MACD策略 ====================

def macd_signal(data: List[Dict], params: Dict) -> str:
    """
    MACD策略
    
    原理:
    - MACD线上穿信号线 -> 买入
    - MACD线下穿信号线 -> 卖出
    """
    fast = params.get('fast', 12)
    slow = params.get('slow', 26)
    signal = params.get('signal', 9)
    
    if len(data) < slow + signal + 1:
        return "HOLD"
    
    closes = pd.Series([float(d["close"]) for d in data])
    
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    
    macd_now = macd.iloc[-1]
    macd_prev = macd.iloc[-2]
    signal_now = signal_line.iloc[-1]
    signal_prev = signal_line.iloc[-2]
    
    # 金叉
    if macd_prev <= signal_prev and macd_now > signal_now:
        return "BUY"
    
    # 死叉
    if macd_prev >= signal_prev and macd_now < signal_now:
        return "SELL"
    
    return "HOLD"


# ==================== 通道突破 ====================

def channel_breakout_signal(data: List[Dict], params: Dict) -> str:
    """
    通道突破策略
    
    原理:
    - 突破20日高点买入
    - 跌破20日低点卖出
    """
    period = params.get('period', 20)
    
    if len(data) < period + 1:
        return "HOLD"
    
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    closes = [float(d["close"]) for d in data]
    
    channel_high = max(highs[-period:-1])
    channel_low = min(lows[-period:-1])
    
    current = closes[-1]
    prev = closes[-2]
    
    # 突破高点
    if prev < channel_high and current > channel_high:
        return "BUY"
    
    # 跌破低点
    if prev > channel_low and current < channel_low:
        return "SELL"
    
    return "HOLD"


# ==================== KDJ策略 ====================

def kdj_signal(data: List[Dict], params: Dict) -> str:
    """
    KDJ随机指标策略
    
    原理:
    - K线 < 20超卖 -> 买入
    - K线 > 80超买 -> 卖出
    """
    period = params.get('period', 9)
    k_period = params.get('k_period', 3)
    d_period = params.get('d_period', 3)
    
    if len(data) < period + 1:
        return "HOLD"
    
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    closes = [float(d["close"]) for d in data]
    
    # 计算RSV
    rsv = []
    for i in range(period, len(closes) + 1):
        n_high = max(highs[i-period:i])
        n_low = min(lows[i-period:i])
        if n_high != n_low:
            rsv_val = (closes[i-1] - n_low) / (n_high - n_low) * 100
        else:
            rsv_val = 50
        rsv.append(rsv_val)
    
    if len(rsv) < k_period:
        return "HOLD"
    
    # K线
    k = np.mean(rsv[-k_period:])
    # D线
    d = np.mean(rsv[-d_period:])
    
    k_prev = np.mean(rsv[-k_period-1:-1])
    d_prev = np.mean(rsv[-d_period-1:-1])
    
    # 买入: 金叉且K<20
    if k_prev < d_prev and k > d and k < 20:
        return "BUY"
    
    # 卖出: 死叉且K>80
    if k_prev > d_prev and k < d and k > 80:
        return "SELL"
    
    return "HOLD"


# ==================== 多策略组合 ====================

def multi_strategy_signal(data: List[Dict], params: Dict) -> str:
    """
    多策略组合信号
    
    原理:
    - 结合多个策略
    - 多数策略同一方向时执行
    """
    # 各策略投票
    votes = {"BUY": 0, "SELL": 0}
    
    strategies = [
        lambda d: ma_cross_signal(d, {'fast': 10, 'slow': 50}),
        lambda d: bollinger_reversion_signal(d, {'period': 20}),
        lambda d: momentum_signal(d, {'lookback': 20, 'threshold': 0.05}),
        lambda d: macd_signal(d, {}),
    ]
    
    for s in strategies:
        signal = s(data)
        votes[signal] = votes.get(signal, 0) + 1
    
    # 3/4策略同一方向
    if votes["BUY"] >= 3:
        return "BUY"
    if votes["SELL"] >= 3:
        return "SELL"
    
    return "HOLD"


# ==================== 策略注册 ====================

STRATEGY_REGISTRY = {
    "turtle": {
        "name": "海龟交易法则",
        "func": turtle_signal,
        "params": {"entry_period": 20, "exit_period": 10}
    },
    "ma_cross": {
        "name": "均线交叉",
        "func": ma_cross_signal,
        "params": {"fast": 10, "slow": 50}
    },
    "bollinger_reversion": {
        "name": "布林带回归",
        "func": bollinger_reversion_signal,
        "params": {"period": 20, "std_dev": 2.0}
    },
    "momentum": {
        "name": "动量策略",
        "func": momentum_signal,
        "params": {"lookback": 20, "threshold": 0.05}
    },
    "macd": {
        "name": "MACD策略",
        "func": macd_signal,
        "params": {"fast": 12, "slow": 26, "signal": 9}
    },
    "channel": {
        "name": "通道突破",
        "func": channel_breakout_signal,
        "params": {"period": 20}
    },
    "kdj": {
        "name": "KDJ策略",
        "func": kdj_signal,
        "params": {"period": 9}
    },
    "multi": {
        "name": "多策略组合",
        "func": multi_strategy_signal,
        "params": {}
    },
}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 生成模拟数据
    data = []
    price = 100
    for i in range(200):
        price *= 1 + random.uniform(-0.02, 0.025)
        data.append({
            'date': f'2024-01-{i+1:02d}',
            'open': price * 0.99,
            'high': price * 1.01,
            'low': price * 0.99,
            'close': price,
            'volume': random.randint(1000000, 5000000)
        })
    
    # 测试各策略
    print("策略信号测试:")
    for name, info in STRATEGY_REGISTRY.items():
        signal = info["func"](data, info["params"])
        print(f"  {info['name']}: {signal}")
