#!/usr/bin/env python3
"""
简化回测 - 基于现有数据优化
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET
import numpy as np

def get_data():
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    import time
    start = int((time.time() - 1095*24*60*60)*1000)
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', limit=3000)
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

def run_test(params, closes):
    rsi_oversold = params['rsi_oversold']
    rsi_overbought = params['rsi_overbought']
    leverage = params['leverage']
    
    initial = 10000
    capital = initial
    position = 0
    entry = 0
    trades = []
    
    for i in range(30, len(closes)):
        data = closes[:i+1]
        
        ma10 = calculate_ma(data, 10)
        ma20 = calculate_ma(data, 20)
        ma50 = calculate_ma(data, 50) if len(data) >= 50 else ma20
        rsi = calculate_rsi(data)
        
        trend = "bull" if ma10 > ma50 else "bear"
        
        # 交易逻辑
        if trend == "bull" and rsi < rsi_oversold and position == 0:
            position = (capital * 0.3) / closes[i]
            entry = closes[i]
            
        elif trend == "bear" and rsi > rsi_overbought and position > 0:
            pnl = (closes[i] - entry) / entry * leverage * 100
            capital = position * closes[i]
            trades.append(pnl)
            position = 0
    
    final = capital + position * closes[-1]
    return (final - initial) / initial * 100, len(trades)

# 获取数据
closes = get_data()
print(f"数据: {len(closes)} 根K线")

# 快速优化
best_ret = -100
best_p = {}

for ro in [25, 30, 35, 40]:
    for rb in [65, 70, 75, 80]:
        for lev in [1, 2, 3]:
            ret, n = run_test({'rsi_oversold': ro, 'rsi_overbought': rb, 'leverage': lev}, closes)
            if n >= 3 and ret > best_ret:
                best_ret = ret
                best_p = {'rsi_oversold': ro, 'rsi_overbought': rb, 'leverage': lev, 'trades': n}

print("=" * 50)
print("最佳参数:")
print(f"  RSI超卖: {best_p.get('rsi_oversold', 'N/A')}")
print(f"  RSI超买: {best_p.get('rsi_overbought', 'N/A')}")
print(f"  杠杆: {best_p.get('leverage', 'N/A')}x")
print(f"  交易次数: {best_p.get('trades', 0)}")
print(f"  收益率: {best_ret:+.1f}%")
print("=" * 50)
