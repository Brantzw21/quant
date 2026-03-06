#!/usr/bin/env python3
"""
优化回测脚本 - 含杠杆/止损/止盈
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET
import numpy as np

def get_data():
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    import time
    start = int((time.time() - 1095*24*60*60)*1000)
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', limit=2000)
    return [float(k[4]) for k in klines]

def calculate_rsi(closes, period=14):
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g = np.mean(gains[-period:])
    avg_l = np.mean(losses[-period:])
    return 100 - (100 / (1 + avg_g/avg_l)) if avg_l > 0 else 50

def calculate_ma(closes, period):
    return np.mean(closes[-period:])

def run_backtest(params):
    """参数化回测"""
    closes = get_data()
    
    # 参数
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)
    stop_loss = params.get('stop_loss', 0.03)  # 3%止损
    take_profit = params.get('take_profit', 0.08)  # 8%止盈
    leverage = params.get('leverage', 3)
    
    initial_capital = 10000
    capital = initial_capital
    position = 0
    entry = 0
    trades = []
    
    for i in range(50, len(closes)):
        data = closes[:i+1]
        
        ma10 = calculate_ma(data, 10)
        ma50 = calculate_ma(data, 50) if len(data) >= 50 else ma10
        rsi = calculate_rsi(data)
        trend = "bull" if ma10 > ma50 else "bear"
        
        # 计算当前仓位价值
        position_value = position * closes[i] if position > 0 else 0
        # 杠杆后的盈亏
        if position > 0 and entry > 0:
            pnl_pct = (closes[i] - entry) / entry * leverage * 100
            
            # 止损
            if pnl_pct <= -stop_loss * 100 * leverage:
                capital = position * closes[i] * (1 - stop_loss)
                trades.append({"pnl": -stop_loss * 100, "type": "SL"})
                position = 0
                entry = 0
                continue
            
            # 止盈
            if pnl_pct >= take_profit * 100 * leverage:
                capital = position * closes[i] * (1 + take_profit)
                trades.append({"pnl": take_profit * 100, "type": "TP"})
                position = 0
                entry = 0
                continue
        
        # 信号
        buy_sig = trend == "bull" and rsi < rsi_oversold
        sell_sig = trend == "bear" and rsi > rsi_overbought
        
        if buy_sig and position == 0:
            # 使用30%仓位 + 杠杆
            use_capital = capital * 0.3
            position = use_capital / closes[i]
            entry = closes[i]
            
        elif sell_sig and position > 0:
            pnl = (closes[i] - entry) / entry * leverage * 100
            capital = position * closes[i]
            trades.append({"pnl": pnl, "type": "SIGNAL"})
            position = 0
            entry = 0
    
    # 最终结算
    final = capital + position * closes[-1]
    return (final - initial_capital) / initial_capital * 100, len(trades), trades

def optimize():
    print("参数优化中...")
    closes = get_data()
    print(f"数据: {len(closes)} 根K线")
    
    best_ret = -100
    best_params = {}
    results = []
    
    # 网格搜索
    for rsi_oversold in [25, 30, 35, 40]:
        for rsi_overbought in [60, 65, 70, 75]:
            for stop_loss in [0.02, 0.03, 0.05]:
                for take_profit in [0.06, 0.08, 0.10]:
                    for leverage in [1, 2, 3]:
                        params = {
                            'rsi_oversold': rsi_oversold,
                            'rsi_overbought': rsi_overbought,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'leverage': leverage
                        }
                        ret, trade_count, _ = run_backtest(params)
                        results.append({
                            'params': params,
                            'return': ret,
                            'trades': trade_count
                        })
    
    # 排序
    results.sort(key=lambda x: x['return'], reverse=True)
    
    print("\n" + "=" * 60)
    print("Top 5 参数组合:")
    for i, r in enumerate(results[:5]):
        p = r['params']
        print(f"{i+1}. RSI({p['rsi_oversold']}/{p['rsi_overbought']}) "
              f"SL:{p['stop_loss']*100:.0f}% TP:{p['take_profit']*100:.0f}% "
              f"Leverage:{p['leverage']}x | 收益:{r['return']:+.1f}% | 交易:{r['trades']}")
    print("=" * 60)
    
    # 最佳
    best = results[0]
    print(f"\n✅ 最佳参数:")
    p = best['params']
    print(f"  RSI超卖: {p['rsi_oversold']}")
    print(f"  RSI超买: {p['rsi_overbought']}")
    print(f"  止损: {p['stop_loss']*100:.0f}%")
    print(f"  止盈: {p['take_profit']*100:.0f}%")
    print(f"  杠杆: {p['leverage']}x")
    print(f"  预期收益: {best['return']:+.1f}%")

if __name__ == "__main__":
    optimize()
