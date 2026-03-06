#!/usr/bin/env python3
"""
A股回测系统
使用项目统一回测引擎
"""
import sys
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from data_manager import MarketDataManager
from strategies.advanced_strategies import *
from strategies.trend_breakout import trend_breakout_signal
from strategies.weekly_strategy import weekly_trend_signal
from strategies import get_strategy
import pandas as pd
from datetime import datetime

def run_astar_backtest(code, name, start, end, strategy_func, params={}, initial_capital=1000000):
    """运行回测"""
    dm = MarketDataManager()
    
    # 获取数据
    df = dm.get_a_stock_klines(code, start, end)
    if not df or len(df) < 50:
        print(f"数据不足: {code}")
        return None
    
    # 转换为回测格式
    data = [{'close': d['close'], 'high': d['high'], 'low': d['low'], 'volume': d['volume']} for d in df]
    
    # 回测
    capital = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []
    
    for i in range(50, len(data)):
        signal = strategy_func(data[:i+1], params)
        
        if signal == "BUY" and position == 0:
            position = capital / data[i]['close']
            entry_price = data[i]['close']
            trades.append({"type": "BUY", "price": entry_price, "date": df[i]['datetime']})
        
        elif signal == "SELL" and position > 0:
            exit_price = data[i]['close']
            pnl = (exit_price - entry_price) / entry_price * 100
            capital = position * exit_price
            trades.append({"type": "SELL", "price": exit_price, "pnl": pnl, "date": df[i]['datetime']})
            position = 0
        
        equity_curve.append(capital)
    
    # 最终持仓
    if position > 0:
        capital = position * data[-1]['close']
    
    total_return = (capital - initial_capital) / initial_capital * 100
    
    return {
        "code": code,
        "name": name,
        "start": start,
        "end": end,
        "initial_capital": initial_capital,
        "final_capital": capital,
        "total_return": total_return,
        "trades": len(trades),
        "equity_curve": equity_curve
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='A股回测')
    parser.add_argument('--code', default='sz.399006', help='股票代码')
    parser.add_argument('--name', default='创业板', help='名称')
    parser.add_argument('--start', default='2021-01-01', help='开始日期')
    parser.add_argument('--end', default='2026-01-06', help='结束日期')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金')
    parser.add_argument('--strategy', default='momentum', help='策略: momentum/ma_cross/macd/turtle/breakout')
    
    args = parser.parse_args()
    
    # 选择策略
    strategies = {
        'momentum': (momentum_signal, {'period': 20}),
        'ma_cross': (ma_cross_signal, {'fast': 5, 'slow': 20}),
        'macd': (macd_signal, {}),
        'turtle': (turtle_signal, {}),
        'breakout': (trend_breakout_signal, {}),
    }
    
    if args.strategy not in strategies:
        print(f"未知策略: {args.strategy}")
        return
    
    func, params = strategies[args.strategy]
    
    print(f"{'='*60}")
    print(f"A股回测: {args.name} ({args.code})")
    print(f"时间: {args.start} ~ {args.end}")
    print(f"策略: {args.strategy}")
    print(f"初始资金: ¥{args.capital:,.0f}")
    print(f"{'='*60}")
    
    result = run_astar_backtest(args.code, args.name, args.start, args.end, func, params, args.capital)
    
    if result:
        print(f"\n📊 回测结果:")
        print(f"  最终资金: ¥{result['final_capital']:,.0f}")
        print(f"  总收益: {result['total_return']:+.2f}%")
        print(f"  交易次数: {result['trades']}次")


if __name__ == "__main__":
    main()
