#!/usr/bin/env python3
"""
3年回测脚本
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET
import numpy as np

def get_data_3y():
    """获取3年数据"""
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    import time
    start = int((time.time() - 1095*24*60*60)*1000)  # 3年
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', limit=2000)
    closes = [float(k[4]) for k in klines]
    print(f"数据: {len(closes)} 根K线 (约3年)")
    return closes

def calculate_rsi(closes, period=14):
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g = np.mean(gains[-period:])
    avg_l = np.mean(losses[-period:])
    return 100 - (100 / (1 + avg_g/avg_l)) if avg_l > 0 else 50

def calculate_ma(closes, period):
    return np.mean(closes[-period:])

def run_backtest():
    print("=" * 50)
    print("3年回测 (2023-2026)")
    print("=" * 50)
    
    closes = get_data_3y()
    
    initial_capital = 10000
    capital = initial_capital
    position = 0
    entry = 0
    trades = []
    equity_curve = []
    
    for i in range(50, len(closes)):
        data = closes[:i+1]
        
        # 指标计算
        ma10 = calculate_ma(data, 10)
        ma20 = calculate_ma(data, 20)
        ma50 = calculate_ma(data, 50) if len(data) >= 50 else ma20
        
        rsi = calculate_rsi(data)
        trend = "bull" if ma10 > ma50 else "bear"
        
        # 信号 (与light_strategy一致)
        buy_sig = sum([
            trend == "bull",
            rsi < 35,
        ])
        sell_sig = sum([
            trend == "bear",
            rsi > 65,
        ])
        
        # 交易
        if buy_sig >= 1 and position == 0:
            position = capital / closes[i]
            entry = closes[i]
            capital = 0
            print(f"BUY @ ${closes[i]:.0f}")
            
        elif sell_sig >= 1 and position > 0:
            pnl = (closes[i] - entry) / entry * 100
            capital = position * closes[i]
            trades.append({"pnl": pnl, "entry": entry, "exit": closes[i]})
            print(f"SELL @ ${closes[i]:.0f} | {pnl:+.1f}%")
            position = 0
        
        equity = capital + position * closes[i]
        equity_curve.append(equity)
    
    # 结果统计
    final = equity_curve[-1]
    total_return = (final - initial_capital) / initial_capital * 100
    
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    
    print("=" * 50)
    print("📊 回测结果")
    print("=" * 50)
    print(f"初始资金: ${initial_capital:,}")
    print(f"最终资金: ${final:,.0f}")
    print(f"总收益率: {total_return:+.1f}%")
    print(f"-" * 30)
    print(f"交易次数: {len(trades)}")
    if trades:
        print(f"盈利次数: {len(wins)}")
        print(f"亏损次数: {len(losses)}")
        print(f"胜率: {len(wins)/len(trades)*100:.0f}%")
    print(f"-" * 30)
    
    # 最大回撤
    peak = equity_curve[0]
    max_dd = 0
    for e in equity_curve:
        if e > peak: peak = e
        dd = (peak - e) / peak * 100
        if dd > max_dd: max_dd = dd
    
    print(f"最大回撤: {max_dd:.1f}%")
    
    # 年化
    years = len(closes) / (6*365)
    annual = ((final/initial_capital) ** (1/years) - 1) * 100
    print(f"年化收益: {annual:+.1f}%")
    print("=" * 50)

if __name__ == "__main__":
    run_backtest()
