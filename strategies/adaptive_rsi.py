"""
自适应RSI策略
参数根据市场波动率自动调整
"""
import numpy as np


def adaptive_rsi_signal(data, params):
    """
    自适应RSI策略
    - 高波动: 更宽的阈值(更少交易)
    - 低波动: 更窄的阈值(更多交易)
    - RSI周期根据波动率自适应
    """
    base_period = params.get('base_period', 14)
    vol_lookback = params.get('vol_lookback', 20)
    
    if len(data) < vol_lookback + base_period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    returns = np.diff(closes) / closes[:-1]
    volatility = np.std(returns[-vol_lookback:]) * np.sqrt(252)
    
    if volatility > 0.3:
        rsi_period = min(21, int(base_period * 1.5))
        oversold = 15
        overbought = 85
    elif volatility > 0.2:
        rsi_period = base_period
        oversold = 20
        overbought = 80
    elif volatility > 0.15:
        rsi_period = max(7, int(base_period * 0.8))
        oversold = 25
        overbought = 75
    else:
        rsi_period = 7
        oversold = 30
        overbought = 70
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        return "HOLD"
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    if rsi < oversold:
        return "BUY"
    elif rsi > overbought:
        return "SELL"
    return "HOLD"


def get_adaptive_rsi_strategy():
    return {
        "name": "自适应RSI",
        "signal_func": adaptive_rsi_signal,
        "default_params": {
            "base_period": 14,
            "vol_lookback": 20
        },
        "param_grid": {
            "base_period": [10, 14, 18],
            "vol_lookback": [15, 20, 30]
        }
    }
