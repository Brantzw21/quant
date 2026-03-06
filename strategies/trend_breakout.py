"""
趋势突破策略 - Trend Breakout Strategy
==========================================

核心逻辑:
- 突破N日高点买入
- 跌破N日低点卖出
- 最低持有M天

适用市场:
- BTC等趋势明显的市场
- 数字货币
- 期货趋势跟踪

参数:
- lookback: 突破周期 (默认30)
- min_hold: 最低持有天数 (默认3)
- position_pct: 仓位比例 (默认0.95)

作者: AI量化系统
"""

import numpy as np
from typing import List, Dict, Tuple


def trend_breakout_signal(data: List[Dict], params: Dict) -> str:
    """
    趋势突破策略信号生成
    
    Args:
        data: K线数据 [{date, open, high, low, close, volume}, ...]
        params: 参数字典
            - lookback: 回顾周期 (默认30)
            - min_hold: 最低持有天数 (默认3)
    
    Returns:
        "BUY" / "SELL" / "HOLD"
    """
    lookback = params.get('lookback', 30)
    min_hold = params.get('min_hold', 3)
    
    # 数据不足
    if len(data) < lookback + 1:
        return "HOLD"
    
    # 获取价格
    closes = [float(d["close"]) for d in data]
    current_price = closes[-1]
    
    # 计算高低点
    recent_closes = closes[-lookback:-1]  # 不包含当前
    high_point = max(recent_closes)
    low_point = min(recent_closes)
    
    # 买入: 突破30日高点
    if current_price > high_point:
        return "BUY"
    
    # 卖出: 跌破30日低点
    if current_price < low_point:
        return "SELL"
    
    return "HOLD"


def trend_breakout_with_filters(data: List[Dict], params: Dict) -> str:
    """
    趋势突破策略(带过滤条件)
    
    增加:
    - 成交量过滤
    - 波动率过滤
    """
    lookback = params.get('lookback', 30)
    min_hold = params.get('min_hold', 3)
    min_volume = params.get('min_volume', True)  # 是否验证成交量
    vol_threshold = params.get('vol_threshold', 1.5)  # 成交量倍数
    
    if len(data) < lookback + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    volumes = [float(d["volume"]) for d in data]
    current_price = closes[-1]
    current_volume = volumes[-1]
    
    # 计算成交量均线
    vol_ma = np.mean(volumes[-lookback:])
    
    # 成交量过滤: 突破时需要放量
    volume_ok = current_volume > vol_ma * vol_threshold if min_volume else True
    
    recent_closes = closes[-lookback:-1]
    high_point = max(recent_closes)
    low_point = min(recent_closes)
    
    # 买入: 突破 + 放量
    if current_price > high_point and volume_ok:
        return "BUY"
    
    # 卖出: 跌破
    if current_price < low_point:
        return "SELL"
    
    return "HOLD"


def get_trend_breakout_strategy():
    """
    获取策略配置
    """
    return {
        "name": "趋势突破策略",
        "signal_func": trend_breakout_signal,
        "default_params": {
            "lookback": 30,
            "min_hold": 3,
            "position_pct": 0.95
        },
        "param_grid": {
            "lookback": [20, 25, 30, 35, 40],
            "min_hold": [2, 3, 5],
            "position_pct": [0.8, 0.9, 0.95, 1.0]
        },
        "applicable_markets": ["crypto", "futures", "trending_stocks"],
        "description": "突破N日高点买入，跌破N日低点卖出"
    }


# ==================== 回测示例 ====================

if __name__ == "__main__":
    import baostock as bs
    import pandas as pd
    
    # 获取数据
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.000300",  # 沪深300
        "date,close",
        start_date="2023-01-01",
        end_date="2026-02-24",
        frequency="d"
    )
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    bs.logout()
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    data = df.to_dict('records')
    
    # 回测
    params = {"lookback": 30, "min_hold": 3}
    capital = 100000
    cash = capital
    position = 0
    
    for i in range(31, len(data)):
        signal = trend_breakout_signal(data[:i+1], params)
        price = float(data[i]["close"])
        
        if signal == "BUY" and position == 0:
            position = int(cash * 0.95 / price)
            cash -= position * price
            print(f"{data[i]['date']}: BUY @ {price}")
        
        elif signal == "SELL" and position > 0:
            cash += position * price
            print(f"{data[i]['date']}: SELL @ {price}")
            position = 0
    
    if position > 0:
        cash += position * float(data[-1]["close"])
    
    print(f"\n收益: {(cash - capital) / capital:.2%}")
