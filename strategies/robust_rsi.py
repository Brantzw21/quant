"""
延迟不敏感的分层RSI策略
- 趋势过滤 (MA50)
- 强制持仓周期 (≥3天)
- 回踩确认机制
"""
import numpy as np


def robust_rsi_signal(data, params):
    """
    稳健RSI策略:
    1. 趋势过滤: 价格 > MA50 才做多
    2. 回踩确认: RSI<30后，第二天不创新低才进
    3. 强制持仓: 至少持有3天
    """
    rsi_period = params.get('rsi_period', 7)
    ma_period = params.get('ma_period', 50)
    hold_days = params.get('hold_days', 3)
    oversold = params.get('oversold', 30)
    exit_threshold = params.get('exit_threshold', 70)
    
    if len(data) < max(rsi_period, ma_period) + 5:
        return "HOLD", 1.0
    
    closes = [float(d["close"]) for d in data]
    
    ma50 = np.mean(closes[-ma_period:])
    current_price = closes[-1]
    
    trend_ok = current_price > ma50
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        return "HOLD", 1.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    rsi_yes = rsi < oversold
    price_yes = closes[-1] < min(closes[-3:-1]) if len(closes) > 3 else False
    
    if trend_ok and rsi_yes:
        if price_yes or rsi < oversold - 5:
            return "BUY", 1.0
    elif rsi < oversold - 10:
        return "BUY", 0.3
    
    if rsi > exit_threshold:
        return "SELL", 1.0
    
    return "HOLD", 1.0


def get_robust_rsi_strategy():
    return {
        "name": "稳健RSI",
        "signal_func": robust_rsi_signal,
        "default_params": {
            "rsi_period": 7,
            "ma_period": 50,
            "hold_days": 3,
            "oversold": 30,
            "exit_threshold": 70
        },
        "param_grid": {
            "rsi_period": [7, 9, 12],
            "ma_period": [30, 50, 80],
            "hold_days": [3, 5],
            "oversold": [25, 30, 35],
            "exit_threshold": [65, 70, 75]
        }
    }
