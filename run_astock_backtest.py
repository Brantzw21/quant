#!/usr/bin/env python3
"""
A股回测兼容入口

说明：
- 当前统一回测入口为 unified_backtest.py
- 本文件保留 A股快捷调用方式，底层转发到统一主框架
"""

import argparse
import sys

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from unified_backtest import run_backtest


def main():
    parser = argparse.ArgumentParser(description='A股回测兼容入口')
    parser.add_argument('--code', default='sz.399006', help='股票代码')
    parser.add_argument('--start', default='2021-01-01', help='开始日期')
    parser.add_argument('--end', default='2026-01-06', help='结束日期')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金')
    parser.add_argument('--strategy', default='momentum', help='策略 key')
    args = parser.parse_args()

    result = run_backtest('a_stock', args.code, args.start, args.end, args.strategy, args.capital)
    if result.get('error'):
        print(result['error'])
        return

    print(f"A股回测: {args.code}")
    print(f"策略: {result['strategy_name']}")
    print(f"总收益: {result['total_return']:+.2%}")
    print(f"最大回撤: {result['max_drawdown']:.2%}")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"卖出次数: {result['sell_trades']}")


if __name__ == '__main__':
    main()
