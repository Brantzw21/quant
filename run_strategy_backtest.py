#!/usr/bin/env python3
"""
策略回测脚本 - 增强版 (含成交量确认)
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET
import numpy as np

def get_data():
    """获取历史数据"""
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    import time
    start = int((time.time() - 365*24*60*60)*1000)
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', startTime=start, limit=1000)
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    return closes, volumes

def run_backtest():
    print("=" * 50)
    print("BTC 4小时策略回测 (1年) - 增强版")
    print("=" * 50)
    
    closes, volumes = get_data()
    print(f"数据: {len(closes)} 根K线")
    
    capital = 10000
    position = 0
    entry = 0
    trades = []
    
    for i in range(50, len(closes)):
        data = closes[:i+1]
        vols = volumes[:i+1]
        
        # 基础指标
        ma10 = np.mean(data[-10:])
        ma20 = np.mean(data[-20:])
        ma50 = np.mean(data[-50:]) if len(data) >= 50 else ma20
        
        # RSI
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_g = np.mean(gains[-21:])
        avg_l = np.mean(losses[-21:])
        rsi = 100 - (100 / (1 + avg_g/avg_l)) if avg_l > 0 else 50
        
        # MACD
        ema12 = np.mean(data[-12:])
        ema26 = np.mean(data[-26:])
        macd = ema12 - ema26
        
        # 成交量确认 (增加20日均量)
        vol_ma20 = np.mean(vols[-20:])
        vol_now = vols[-1]
        volume_confirm = vol_now > vol_ma20  # 放量
        
        # 趋势
        trend = "bull" if ma10 > ma50 else "bear"
        
        # 信号 (加入成交量确认)
        buy_sig = sum([
            trend == "bull",
            rsi < 30,  # 更严格
            macd > 0,
            volume_confirm  # 成交量确认
        ])
        
        sell_sig = sum([
            trend == "bear",
            rsi > 70,
            macd < 0,
            volume_confirm
        ])
        
        if buy_sig >= 3 and position == 0:
            position = capital / closes[i]
            entry = closes[i]
            capital = 0
            print(f"BUY @ ${closes[i]:.0f} (sig:{buy_sig})")
        elif sell_sig >= 3 and position > 0:
            pnl = (closes[i] - entry) / entry * 100
            capital = position * closes[i]
            trades.append(pnl)
            print(f"SELL @ ${closes[i]:.0f} | {pnl:+.1f}%")
            position = 0
    
    # 结果
    final = capital + position * closes[-1]
    ret = (final - 10000) / 10000 * 100
    
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    
    print("=" * 50)
    print(f"初始: $10,000 -> 最终: ${final:,.0f}")
    print(f"收益率: {ret:+.1f}%")
    print(f"交易次数: {len(trades)}")
    if trades:
        print(f"胜率: {len(wins)/len(trades)*100:.0f}% (W:{len(wins)} L:{len(losses)})")
    print("=" * 50)

if __name__ == "__main__":
    run_backtest()
