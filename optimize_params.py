#!/usr/bin/env python3
"""
参数优化脚本
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
    start = int((time.time() - 365*24*60*60)*1000)
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', startTime=start, limit=1000)
    return [float(k[4]) for k in klines]

def backtest(closes, rsi_oversold, rsi_overbought):
    capital = 10000
    position = 0
    entry = 0
    trades = []
    
    for i in range(50, len(closes)):
        data = closes[:i+1]
        
        ma10 = np.mean(data[-10:])
        ma50 = np.mean(data[-50:]) if len(data) >= 50 else ma10
        
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_g = np.mean(gains[-14:])
        avg_l = np.mean(losses[-14:])
        rsi = 100 - (100 / (1 + avg_g/avg_l)) if avg_l > 0 else 50
        
        ema12 = np.mean(data[-12:])
        ema26 = np.mean(data[-26:])
        macd = ema12 - ema26
        
        trend = "bull" if ma10 > ma50 else "bear"
        
        buy_sig = (trend == "bull" and rsi < rsi_oversold and macd > 0)
        sell_sig = (trend == "bear" and rsi > rsi_overbought and macd < 0)
        
        if buy_sig and position == 0:
            position = capital / closes[i]
            entry = closes[i]
            capital = 0
        elif sell_sig and position > 0:
            pnl = (closes[i] - entry) / entry * 100
            capital = position * closes[i]
            trades.append(pnl)
            position = 0
    
    final = capital + position * closes[-1]
    return (final - 10000) / 10000 * 100, len(trades)

def optimize():
    print("参数优化中...")
    closes = get_data()
    
    results = []
    
    for rsi_oversold in [20, 25, 30, 35, 40]:
        for rsi_overbought in [60, 65, 70, 75, 80, 85]:
            ret, trades = backtest(closes, rsi_oversold, rsi_overbought)
            results.append({
                "oversold": rsi_oversold,
                "overbought": rsi_overbought,
                "return": ret,
                "trades": trades
            })
    
    # 排序
    results.sort(key=lambda x: x["return"], reverse=True)
    
    print("\n" + "=" * 50)
    print("Top 5 参数组合:")
    for i, r in enumerate(results[:5]):
        print(f"{i+1}. RSI({r['oversold']}/{r['overbought']}): 收益 {r['return']:+.1f}% | 交易 {r['trades']}次")
    print("=" * 50)
    
    # 最佳参数
    best = results[0]
    print(f"\n最佳参数: RSI超卖={best['oversold']}, RSI超买={best['overbought']}")
    print(f"预期收益: {best['return']:+.1f}%")

if __name__ == "__main__":
    optimize()
