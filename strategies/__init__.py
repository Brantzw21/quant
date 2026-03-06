"""
策略模块 - 交易信号生成
"""

import numpy as np


def ma_cross_signal(data, params):
    """
    均线交叉策略
    买入: 短期MA上穿长期MA
    卖出: 短期MA下穿长期MA
    """
    fast = params.get('fast_ma', 5)
    slow = params.get('slow_ma', 20)
    
    if len(data) < slow + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    ma_fast = sum(closes[-fast:]) / fast
    ma_slow = sum(closes[-slow:]) / slow
    prev_ma_fast = sum(closes[-fast-1:-1]) / fast
    prev_ma_slow = sum(closes[-slow-1:-1]) / slow
    
    if prev_ma_fast <= prev_ma_slow and ma_fast > ma_slow:
        return "BUY"
    elif prev_ma_fast >= prev_ma_slow and ma_fast < ma_slow:
        return "SELL"
    return "HOLD"


def rsi_signal(data, params):
    """
    RSI均值回归策略
    买入: RSI < oversold (超卖)
    卖出: RSI > overbought (超买)
    """
    period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    
    if len(data) < period + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return "HOLD"
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    if rsi < oversold:
        return "BUY"
    elif rsi > overbought:
        return "SELL"
    return "HOLD"


def breakout_signal(data, params):
    """
    突破策略
    买入: 价格突破近期高点
    卖出: 价格跌破近期低点
    """
    lookback = params.get('lookback', 20)
    factor = params.get('breakout_factor', 1.02)
    
    if len(data) < lookback + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    
    current_price = closes[-1]
    prev_price = closes[-2]
    recent_high = max(highs[-lookback:-1])
    recent_low = min(lows[-lookback:-1])
    
    if prev_price < recent_high * factor and current_price > recent_high * factor:
        return "BUY"
    elif prev_price > recent_low / factor and current_price < recent_low / factor:
        return "SELL"
    return "HOLD"


def dual_ma_rsi_signal(data, params):
    """
    双均线+RSI组合策略
    买入: 均线多头且RSI在阈值上方
    卖出: 均线空头或RSI在阈值下方
    """
    fast_ma = params.get('fast_ma', 10)
    slow_ma = params.get('slow_ma', 30)
    rsi_period = params.get('rsi_period', 14)
    rsi_thresh = params.get('rsi_threshold', 50)
    
    if len(data) < slow_ma + 1:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    ma_fast = sum(closes[-fast_ma:]) / fast_ma
    ma_slow = sum(closes[-slow_ma:]) / slow_ma
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    if ma_fast > ma_slow and rsi > rsi_thresh:
        return "BUY"
    elif ma_fast < ma_slow or rsi < rsi_thresh:
        return "SELL"
    return "HOLD"


STRATEGY_REGISTRY = {
    "ma_cross": {
        "name": "均线交叉",
        "signal_func": ma_cross_signal,
        "default_params": {"fast_ma": 5, "slow_ma": 20},
        "param_grid": {
            "fast_ma": [3, 5, 8, 10, 15, 20, 30, 40, 50],
            "slow_ma": [10, 20, 30, 50, 80, 100, 150, 200]
        },
        "constraints": {"fast_ma": "less_than_slow_ma"}
    },
    "rsi": {
        "name": "RSI均值回归",
        "signal_func": rsi_signal,
        "default_params": {"rsi_period": 14, "oversold": 30, "overbought": 70},
        "param_grid": {
            "rsi_period": [7, 9, 12, 14, 18, 21],
            "oversold": [20, 25, 30, 35],
            "overbought": [65, 70, 75, 80]
        },
        "constraints": {"oversold": "less_than_overbought"}
    },
    "breakout": {
        "name": "突破策略",
        "signal_func": breakout_signal,
        "default_params": {"lookback": 20, "breakout_factor": 1.02},
        "param_grid": {
            "lookback": [5, 10, 15, 20, 30, 40, 50, 60],
            "breakout_factor": [1.005, 1.01, 1.02, 1.03, 1.04, 1.05]
        }
    },
    "dual_ma_rsi": {
        "name": "双均线RSI",
        "signal_func": dual_ma_rsi_signal,
        "default_params": {"fast_ma": 10, "slow_ma": 30, "rsi_period": 14, "rsi_threshold": 50},
        "param_grid": {
            "fast_ma": [3, 5, 8, 10, 15, 20, 30],
            "slow_ma": [15, 20, 30, 50, 80, 100],
            "rsi_period": [5, 7, 9, 14, 21],
            "rsi_threshold": [30, 40, 50, 60, 70]
        },
        "constraints": {"fast_ma": "less_than_slow_ma"}
    },
    "adaptive_rsi": {
        "name": "自适应RSI",
        "signal_func": None,
        "default_params": {"base_period": 14, "vol_lookback": 20},
        "param_grid": {
            "base_period": [10, 14, 18],
            "vol_lookback": [15, 20, 30]
        }
    },
    "layered_rsi": {
        "name": "分层RSI",
        "signal_func": None,
        "default_params": {"rsi_period": 7, "light_threshold": 35, "full_threshold": 30, "exit_threshold": 60},
        "param_grid": {
            "rsi_period": [7, 9, 12],
            "light_threshold": [35, 40],
            "full_threshold": [25, 30],
            "exit_threshold": [60, 65]
        }
    },
    "robust_rsi": {
        "name": "稳健RSI",
        "signal_func": None,
        "default_params": {"rsi_period": 7, "ma_period": 50, "hold_days": 3, "oversold": 30, "exit_threshold": 70},
        "param_grid": {
            "rsi_period": [7, 9, 12],
            "ma_period": [30, 50, 80],
            "hold_days": [3, 5],
            "oversold": [25, 30, 35],
            "exit_threshold": [65, 70, 75]
        }
    }
}


def get_strategy(name):
    """获取策略配置"""
    strategy = STRATEGY_REGISTRY.get(name)
    if strategy is None:
        return None
    
    result = strategy.copy()
    
    if result.get("signal_func") is None:
        if name == "adaptive_rsi":
            from strategies.adaptive_rsi import adaptive_rsi_signal
            result["signal_func"] = adaptive_rsi_signal
        elif name == "layered_rsi":
            from strategies.layered_rsi import layered_rsi_signal
            result["signal_func"] = layered_rsi_signal
        elif name == "robust_rsi":
            from strategies.robust_rsi import robust_rsi_signal
            result["signal_func"] = robust_rsi_signal
    
    return result


def list_strategies():
    """列出所有可用策略"""
    return [(k, v["name"]) for k, v in STRATEGY_REGISTRY.items()]
