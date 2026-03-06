#!/usr/bin/env python3
"""
统一回测系统 - 支持所有市场
A股、数字货币、ETF等
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import MarketDataManager, FuturesDataManager
from strategies.advanced_strategies import *
from strategies.trend_breakout import trend_breakout_signal
from strategies.weekly_strategy import weekly_trend_signal
import pandas as pd
from datetime import datetime

# 支持的市场
MARKETS = {
    "a_stock": {
        "name": "A股",
        "examples": ["sh.000300", "sz.399006", "sh.510300"],
        "get_data": "get_a_stock_klines"
    },
    "crypto": {
        "name": "加密货币",
        "examples": ["BTCUSDT", "ETHUSDT"],
        "get_data": "get_binance_klines"
    },
    "forex": {
        "name": "外汇",
        "examples": ["EURUSD", "GBPUSD"],
        "get_data": "get_forex_klines"
    }
}

# 支持的策略
STRATEGIES = {
    "momentum": ("动量策略", momentum_signal, {'period': 20}),
    "ma_cross": ("均线交叉", ma_cross_signal, {'fast': 5, 'slow': 20}),
    "macd": ("MACD", macd_signal, {}),
    "turtle": ("海龟策略", turtle_signal, {}),
    "breakout": ("趋势突破", trend_breakout_signal, {}),
    "channel": ("通道突破", channel_breakout_signal, {}),
    "weekly": ("周线策略", weekly_trend_signal, {}),
}


def get_data(market, symbol, start, end):
    """获取市场数据"""
    dm = MarketDataManager()
    fdm = FuturesDataManager()
    
    if market == "a_stock":
        return dm.get_a_stock_klines(symbol, start, end)
    elif market == "crypto":
        return fdm.get_binance_klines(symbol, "1d", start, end)
    elif market == "forex":
        return dm.get_forex_klines(symbol, start, end)
    return None


def run_backtest(market, symbol, start, end, strategy_func, params={}, initial_capital=1000000):
    """运行回测"""
    # 获取数据
    df = get_data(market, symbol, start, end)
    
    if not df or len(df) < 50:
        print(f"数据不足: {symbol}")
        return None
    
    # 转换为回测格式
    data = []
    for d in df:
        if 'close' in d:
            data.append({
                'close': d['close'], 
                'high': d.get('high', d['close']), 
                'low': d.get('low', d['close']),
                'volume': d.get('volume', 0)
            })
    
    if len(data) < 50:
        return None
    
    # 回测
    capital = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity = []
    
    for i in range(50, len(data)):
        signal = strategy_func(data[:i+1], params)
        
        if signal == "BUY" and position == 0:
            position = capital / data[i]['close']
            entry_price = data[i]['close']
            trades.append({"type": "BUY", "price": entry_price})
        
        elif signal == "SELL" and position > 0:
            exit_price = data[i]['close']
            pnl = (exit_price - entry_price) / entry_price * 100
            capital = position * exit_price
            trades.append({"type": "SELL", "price": exit_price, "pnl": pnl})
            position = 0
        
        equity.append(capital)
    
    if position > 0:
        capital = position * data[-1]['close']
    
    total_return = (capital - initial_capital) / initial_capital * 100
    wins = len([t for t in trades if t.get('pnl', 0) > 0])
    win_rate = wins / (len(trades)/2) * 100 if trades else 0
    
    return {
        "symbol": symbol,
        "start": start,
        "end": end,
        "initial": initial_capital,
        "final": capital,
        "return": total_return,
        "trades": len(trades),
        "win_rate": win_rate,
        "equity": equity
    }


def compare_strategies(market, symbol, start, end, initial_capital=1000000):
    """对比所有策略"""
    print(f"\n{'='*60}")
    print(f"策略对比 - {symbol} ({start} ~ {end})")
    print(f"{'='*60}")
    
    results = []
    
    for name, (desc, func, params) in STRATEGIES.items():
        result = run_backtest(market, symbol, start, end, func, params, initial_capital)
        if result:
            results.append((desc, result))
            print(f"  {desc}: {result['return']:+.1f}% ({result['trades']}次, 胜率{result['win_rate']:.0f}%)")
    
    results.sort(key=lambda x: x[1]['return'], reverse=True)
    
    print(f"\n🏆 最佳策略: {results[0][0]}")
    
    return results


def compare_markets(symbols, start, end, strategy="momentum", initial_capital=1000000):
    """对比多个市场"""
    print(f"\n{'='*60}")
    print(f"市场对比 - {strategy}策略 ({start} ~ {end})")
    print(f"{'='*60}")
    
    _, func, params = STRATEGIES[strategy]
    
    for symbol in symbols:
        result = run_backtest("crypto", symbol, start, end, func, params, initial_capital)
        if result:
            print(f"  {symbol}: {result['return']:+.1f}% ({result['trades']}次)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='统一回测系统')
    
    parser.add_argument('--market', '-m', default='a_stock', 
                       choices=['a_stock', 'crypto', 'forex'],
                       help='市场类型')
    parser.add_argument('--symbol', '-s', default='sz.399006',
                       help='交易标的')
    parser.add_argument('--start', default='2021-01-01',
                       help='开始日期')
    parser.add_argument('--end', default='2026-01-06',
                       help='结束日期')
    parser.add_argument('--capital', type=float, default=1000000,
                       help='初始资金')
    parser.add_argument('--strategy', default='momentum',
                       choices=list(STRATEGIES.keys()),
                       help='交易策略')
    parser.add_argument('--compare', action='store_true',
                       help='对比所有策略')
    
    args = parser.parse_args()
    
    if args.compare:
        # 对比所有策略
        compare_strategies(args.market, args.symbol, args.start, args.end, args.capital)
    else:
        # 单策略回测
        _, func, params = STRATEGIES[args.strategy]
        
        print(f"{'='*60}")
        print(f"回测: {args.symbol}")
        print(f"市场: {args.market}, 策略: {args.strategy}")
        print(f"时间: {args.start} ~ {args.end}")
        print(f"资金: ¥{args.capital:,.0f}")
        print(f"{'='*60}")
        
        result = run_backtest(args.market, args.symbol, args.start, args.end, 
                            func, params, args.capital)
        
        if result:
            print(f"\n📊 结果:")
            print(f"  最终资金: ¥{result['final']:,.0f}")
            print(f"  总收益: {result['return']:+.2f}%")
            print(f"  交易次数: {result['trades']}次")
            print(f"  胜率: {result['win_rate']:.1f}%")


if __name__ == "__main__":
    main()
