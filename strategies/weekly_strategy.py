"""
周线级别趋势策略 - Weekly Trend Strategy
==========================================

特点:
- 周线级别，更稳定
- 不受T+1限制
- 适合长线资金

适用:
- 1500美元小资金
- 现金账户
- 长线投资者

作者: AI量化系统
"""

import numpy as np
from typing import List, Dict


def weekly_trend_signal(data: List[Dict], params: Dict) -> str:
    """
    周线趋势策略
    
    逻辑:
    - 周收盘价突破10周均线 → 买入
    - 周收盘价跌破10周均线 → 卖出
    
    参数:
    - ma_period: 均线周期 (默认10)
    - confirm_weeks: 确认周数 (默认1)
    """
    ma_period = params.get('ma_period', 10)
    confirm_weeks = params.get('confirm_weeks', 1)
    
    if len(data) < ma_period + confirm_weeks:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    # 周均线
    ma = np.mean(closes[-ma_period:])
    current = closes[-1]
    prev = closes[-2]
    
    # 买入: 突破均线
    if prev <= ma and current > ma:
        return "BUY"
    
    # 卖出: 跌破均线
    if prev >= ma and current < ma:
        return "SELL"
    
    return "HOLD"


def weekly_breakout_signal(data: List[Dict], params: Dict) -> str:
    """
    周线突破策略
    
    逻辑:
    - 突破20周高点 → 买入
    - 跌破20周低点 → 卖出
    """
    lookback = params.get('lookback', 20)
    
    if len(data) < lookback + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    high_20 = max(closes[-lookback:-1])
    low_20 = min(closes[-lookback:-1])
    
    current = closes[-1]
    prev = closes[-2]
    
    # 买入
    if prev < high_20 and current > high_20:
        return "BUY"
    
    # 卖出
    if prev > low_20 and current < low_20:
        return "SELL"
    
    return "HOLD"


def dual_weekly_signal(data: List[Dict], params: Dict) -> str:
    """
    双周线策略
    
    结合:
    - 10周均线趋势
    - 20周高低点突破
    """
    ma_period = params.get('ma_period', 10)
    lookback = params.get('lookback', 20)
    
    if len(data) < max(ma_period, lookback) + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    # 均线
    ma10 = np.mean(closes[-ma_period:])
    
    # 区间
    high_20 = max(closes[-lookback:-1])
    low_20 = min(closes[-lookback:-1])
    
    current = closes[-1]
    prev = closes[-2]
    
    # 买入条件: 均线向上 + 突破20周高点
    trend_up = ma10 > np.mean(closes[-(ma_period+5):-ma_period])
    breakout = prev < high_20 and current > high_20
    
    if trend_up and breakout:
        return "BUY"
    
    # 卖出条件: 均线向下 + 跌破20周低点
    trend_down = ma10 < np.mean(closes[-(ma_period+5):-ma_period])
    breakdown = prev > low_20 and current < low_20
    
    if trend_down and breakdown:
        return "SELL"
    
    return "HOLD"


def get_weekly_strategy():
    """获取策略配置"""
    return {
        "name": "周线趋势策略",
        "signal_func": weekly_trend_signal,
        "default_params": {
            "ma_period": 10,
            "confirm_weeks": 1,
        },
        "param_grid": {
            "ma_period": [8, 10, 12, 15],
            "confirm_weeks": [1, 2],
        },
        "applicable_markets": ["us_stocks", "etfs"],
        "description": "周线级别趋势跟踪，适合长线投资"
    }


# ==================== 回测示例 ====================

if __name__ == "__main__":
    # 模拟周线数据
    import random
    random.seed(42)
    
    # 生成模拟数据 (周线, 5年)
    data = []
    price = 100
    for i in range(260):  # 5年 * 52周
        price *= 1 + random.uniform(-0.03, 0.035)
        data.append({
            'date': f'2020-{i//52+1:02d}-W{i%52+1:02d}',
            'close': price
        })
    
    # 回测
    capital = 1500
    position = 0
    
    for i in range(20, len(data)):
        signal = weekly_trend_signal(data[:i+1], {})
        price = data[i]['close']
        
        if signal == "BUY" and position == 0:
            position = int(capital * 0.95 / price)
            capital -= position * price
            print(f"{data[i]['date']}: BUY {position} @ ${price:.2f}")
        
        elif signal == "SELL" and position > 0:
            capital += position * price
            print(f"{data[i]['date']}: SELL {position} @ ${price:.2f}")
            position = 0
    
    if position > 0:
        capital += position * data[-1]['close']
    
    ret = (capital - 1500) / 1500
    print(f"\n收益: {ret:.2%}")
