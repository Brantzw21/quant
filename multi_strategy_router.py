#!/usr/bin/env python3
"""
策略路由器 - 多策略支持
支持同时运行多个策略并综合信号
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from light_strategy import generate_signal as light_signal
from strategies import STRATEGY_REGISTRY
from binance.client import Client
import json
from datetime import datetime

# 策略权重配置
STRATEGY_WEIGHTS = {
    "light": 0.5,      # 主策略权重
    "ma_cross": 0.2,   # 均线交叉
    "rsi": 0.15,       # RSI
    "breakout": 0.15   # 突破
}

def get_data(symbol="BTCUSDT", interval="4h", limit=100):
    """获取K线数据"""
    from config import API_KEY, SECRET_KEY, TESTNET
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    data = []
    for k in klines:
        data.append({
            "open_time": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return data

def run_sub_strategy(strategy_name, data, params=None):
    """运行子策略"""
    strategy = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy:
        return None
    
    signal_func = strategy.get("signal_func")
    if not signal_func:
        return None
    
    try:
        signal = signal_func(data, params or strategy.get("default_params", {}))
        return signal
    except Exception as e:
        print(f"策略 {strategy_name} 执行失败: {e}")
        return None

def multi_strategy_signal(symbol="BTCUSDT"):
    """
    多策略综合信号
    
    返回: {
        "signal": "BUY/SELL/HOLD",
        "confidence": 0.0-1.0,
        "strategies": {
            "light": {"signal": "BUY", "weight": 0.5},
            ...
        }
    }
    """
    print("=" * 50)
    print("多策略信号分析...")
    
    # 获取数据
    data = get_data(symbol, "4h", 100)
    
    if len(data) < 50:
        print("数据不足")
        return None
    
    # 运行各策略
    strategy_results = {}
    
    # 1. Light策略
    try:
        light = light_signal()
        strategy_results["light"] = {
            "signal": light.get("signal", "HOLD"),
            "confidence": light.get("confidence", 0.5),
            "weight": STRATEGY_WEIGHTS.get("light", 0.5)
        }
    except Exception as e:
        print(f"Light策略失败: {e}")
    
    # 2. 子策略
    for name in ["ma_cross", "rsi", "breakout"]:
        try:
            signal = run_sub_strategy(name, data)
            strategy_results[name] = {
                "signal": signal or "HOLD",
                "confidence": 0.6 if signal in ["BUY", "SELL"] else 0.5,
                "weight": STRATEGY_WEIGHTS.get(name, 0.15)
            }
        except Exception as e:
            print(f"{name}策略失败: {e}")
    
    # 综合评分
    buy_score = 0
    sell_score = 0
    total_weight = 0
    
    for name, result in strategy_results.items():
        weight = result.get("weight", 0)
        signal = result.get("signal", "HOLD")
        
        if signal == "BUY":
            buy_score += weight
        elif signal == "SELL":
            sell_score += weight
        
        total_weight += weight
    
    # 归一化
    if total_weight > 0:
        buy_score /= total_weight
        sell_score /= total_weight
    
    # 最终信号
    if buy_score > 0.4:
        final_signal = "BUY"
        confidence = buy_score
    elif sell_score > 0.4:
        final_signal = "SELL"
        confidence = sell_score
    else:
        final_signal = "HOLD"
        confidence = 0.5
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "signal": final_signal,
        "confidence": confidence,
        "buy_score": round(buy_score, 2),
        "sell_score": round(sell_score, 2),
        "strategies": strategy_results
    }
    
    # 打印结果
    print(f"\n📊 各策略信号:")
    for name, r in strategy_results.items():
        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⏸️"}.get(r["signal"], "❓")
        print(f"  {name}: {emoji} {r['signal']} (权重:{r['weight']})")
    
    print(f"\n📈 综合信号: {final_signal} (置信度: {confidence:.0%})")
    print("=" * 50)
    
    return result

if __name__ == "__main__":
    result = multi_strategy_signal()
    if result:
        # 保存
        with open("/root/.openclaw/workspace/quant_v2/data/multi_strategy_signal.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("结果已保存")
