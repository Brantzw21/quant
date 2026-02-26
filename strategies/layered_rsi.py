"""
分层进场RSI策略
- 扩大触发区间
- 分层进场
- 允许跨regime持仓
"""
import numpy as np


def layered_rsi_signal(data, params):
    """
    分层进场RSI策略
    - 过渡区(30-35): 轻仓20%
    - 信号区(<30): 全仓
    - 高位(>65): 全平
    """
    rsi_period = params.get('rsi_period', 7)
    light_threshold = params.get('light_threshold', 35)
    full_threshold = params.get('full_threshold', 30)
    exit_threshold = params.get('exit_threshold', 65)
    
    if len(data) < rsi_period + 1:
        return "HOLD", 1.0
    
    closes = [float(d["close"]) for d in data]
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        return "HOLD", 1.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    if rsi < full_threshold:
        return "BUY", 1.0
    elif rsi < light_threshold:
        return "BUY", 0.2
    elif rsi > exit_threshold:
        return "SELL", 1.0
    return "HOLD", 1.0


def get_layered_rsi_strategy():
    return {
        "name": "分层RSI",
        "signal_func": layered_rsi_signal,
        "default_params": {
            "rsi_period": 7,
            "light_threshold": 35,
            "full_threshold": 30,
            "exit_threshold": 65
        },
        "param_grid": {
            "rsi_period": [7, 9, 12, 14],
            "light_threshold": [35, 40, 45],
            "full_threshold": [25, 30, 35],
            "exit_threshold": [60, 65, 70]
        }
    }
