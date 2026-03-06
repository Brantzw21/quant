#!/usr/bin/env python3
"""
策略适配器 - 让现有策略兼容回测引擎
"""
import sys
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

# 从strategies导入
from strategies import ma_cross_signal, rsi_signal, breakout_signal, dual_ma_rsi_signal
from strategies.advanced_strategies import (
    turtle_signal, momentum_signal, macd_signal, channel_breakout_signal,
    kdj_signal, bollinger_reversion_signal, multi_strategy_signal
)
from strategies.trend_breakout import trend_breakout_signal, trend_breakout_with_filters
from strategies.weekly_strategy import (
    weekly_trend_signal, weekly_breakout_signal, dual_weekly_signal
)

# 策略注册表
STRATEGY_REGISTRY = {
    # 基础策略
    "ma_cross": {
        "func": ma_cross_signal,
        "params": {"fast": 5, "slow": 20},
        "name": "均线交叉"
    },
    "rsi": {
        "func": rsi_signal,
        "params": {"rsi_period": 14, "oversold": 30, "overbought": 70},
        "name": "RSI均值回归"
    },
    "breakout": {
        "func": breakout_signal,
        "params": {"lookback": 20, "breakout_factor": 1.02},
        "name": "突破策略"
    },
    "dual_ma_rsi": {
        "func": dual_ma_rsi_signal,
        "params": {"fast_ma": 10, "slow_ma": 30, "rsi_period": 14},
        "name": "双均线RSI"
    },
    
    # 高级策略
    "turtle": {
        "func": turtle_signal,
        "params": {},
        "name": "海龟策略"
    },
    "momentum": {
        "func": momentum_signal,
        "params": {"period": 20},
        "name": "动量策略"
    },
    "macd": {
        "func": macd_signal,
        "params": {},
        "name": "MACD"
    },
    "channel_breakout": {
        "func": channel_breakout_signal,
        "params": {},
        "name": "通道突破"
    },
    "kdj": {
        "func": kdj_signal,
        "params": {},
        "name": "KDJ"
    },
    "bollinger_reversion": {
        "func": bollinger_reversion_signal,
        "params": {"period": 20},
        "name": "布林回归"
    },
    
    # 周线策略
    "weekly_trend": {
        "func": weekly_trend_signal,
        "params": {},
        "name": "周线趋势"
    },
    "weekly_breakout": {
        "func": weekly_breakout_signal,
        "params": {},
        "name": "周线突破"
    },
    "dual_weekly": {
        "func": dual_weekly_signal,
        "params": {},
        "name": "双周线"
    },
    
    # 趋势突破
    "trend_breakout": {
        "func": trend_breakout_signal,
        "params": {},
        "name": "趋势突破"
    },
    "trend_breakout_filters": {
        "func": trend_breakout_with_filters,
        "params": {},
        "name": "趋势突破+过滤"
    },
}


def wrap_strategy(strategy_name):
    """
    包装策略函数，使其兼容BacktestEngine
    
    返回: 可直接传给backtest_engine的函数
    """
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {strategy_name}")
    
    info = STRATEGY_REGISTRY[strategy_name]
    func = info["func"]
    params = info["params"]
    
    def wrapper(df):
        """包装函数"""
        try:
            # DataFrame转dict列表
            if hasattr(df, 'to_dict'):
                data = df.to_dict('records')
            else:
                data = df
            
            # 调用策略
            signal = func(data, params)
            
            # 返回字典格式 (兼容backtest_engine)
            return {"signal": signal}
        except Exception as e:
            return {"signal": "HOLD", "error": str(e)}
    
    return wrapper


def list_strategies():
    """列出所有可用策略"""
    return [(k, v["name"]) for k, v in STRATEGY_REGISTRY.items()]


def get_strategy_info(name):
    """获取策略信息"""
    return STRATEGY_REGISTRY.get(name)


# 测试
if __name__ == "__main__":
    print("=== 策略适配器 ===")
    print(f"可用策略: {len(STRATEGY_REGISTRY)}个")
    print()
    for k, v in STRATEGY_REGISTRY.items():
        print(f"  {k}: {v['name']}")
