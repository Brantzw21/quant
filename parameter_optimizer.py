#!/usr/bin/env python3
"""
参数优化器
基于统一回测框架进行网格搜索
"""

import sys
import os
from typing import Dict, List, Type

import pandas as pd

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_framework import Backtester, BacktestConfig, ParameterOptimizer as FrameworkParameterOptimizer, Strategy


class ParameterOptimizer:
    """统一参数优化入口。"""

    def __init__(self, symbol: str = 'BTCUSDT', metric: str = 'sharpe_ratio'):
        self.symbol = symbol
        self.metric = metric
        self.backtester = Backtester(BacktestConfig(symbol=symbol))
        self.optimizer = FrameworkParameterOptimizer(self.backtester)

    def optimize(self, data: pd.DataFrame, strategy_cls: Type[Strategy], param_grid: Dict, top_n: int = 10) -> List[Dict]:
        results = self.optimizer.grid_search(data, strategy_cls, param_grid, top_n=top_n)
        results.sort(key=lambda x: x.get(self.metric, 0), reverse=True)
        return results


if __name__ == '__main__':
    import numpy as np

    class DemoStrategy(Strategy):
        def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
            self.period = period
            self.overbought = overbought
            self.oversold = oversold

        def get_name(self) -> str:
            return f'DemoRSI({self.period},{self.overbought},{self.oversold})'

        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            signals = pd.Series(0, index=data.index)
            signals[rsi < self.oversold] = 1
            signals[rsi > self.overbought] = -1
            return signals.fillna(0)

    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, 200))
    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, 200),
    })

    optimizer = ParameterOptimizer('BTCUSDT')
    top = optimizer.optimize(
        df,
        DemoStrategy,
        {
            'period': [10, 14, 20],
            'overbought': [65, 70, 75],
            'oversold': [25, 30, 35],
        },
        top_n=5,
    )
    for row in top:
        print(row)
