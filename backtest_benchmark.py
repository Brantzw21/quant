#!/usr/bin/env python3
"""
统一回测基准样例
生成可复现的标准回测结果，作为主框架的基准输出。
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_framework import Backtester, BacktestConfig
from unified_backtest import FunctionStrategy, STRATEGIES


@dataclass
class BenchmarkCase:
    name: str
    strategy_key: str
    initial_capital: float = 100000.0
    bars: int = 260
    seed: int = 42


def make_synthetic_ohlcv(bars: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100 * np.cumprod(1 + rng.normal(0.0008, 0.015, bars))
    dates = pd.date_range('2024-01-01', periods=bars, freq='D')
    df = pd.DataFrame({
        'open': prices * (1 - rng.uniform(0.0001, 0.002, bars)),
        'high': prices * (1 + rng.uniform(0.001, 0.015, bars)),
        'low': prices * (1 - rng.uniform(0.001, 0.015, bars)),
        'close': prices,
        'volume': rng.integers(1000, 5000, bars),
    }, index=dates)
    return df


def run_case(case: BenchmarkCase) -> Dict:
    df = make_synthetic_ohlcv(case.bars, case.seed)
    desc, func, params = STRATEGIES[case.strategy_key]
    strategy = FunctionStrategy(desc, func, params)
    backtester = Backtester(BacktestConfig(initial_capital=case.initial_capital, symbol='BENCH'))
    result = backtester.run(df, strategy)
    return {
        'case': asdict(case),
        'strategy_name': desc,
        'summary': {
            'final_equity': round(result['final_equity'], 2),
            'total_return_pct': round(result['total_return'] * 100, 2),
            'annualized_return_pct': round(result['annualized_return'] * 100, 2),
            'max_drawdown_pct': round(result['max_drawdown'] * 100, 2),
            'sharpe_ratio': round(result['sharpe_ratio'], 3),
            'profit_factor': round(result['profit_factor'], 3),
            'sell_trades': result['sell_trades'],
            'win_rate_pct': round(result['win_rate'] * 100, 2),
            'total_commission': round(result['total_commission'], 2),
        },
    }


def run_benchmark_suite() -> Dict:
    cases: List[BenchmarkCase] = [
        BenchmarkCase(name='momentum_baseline', strategy_key='momentum', seed=11),
        BenchmarkCase(name='ma_cross_baseline', strategy_key='ma_cross', seed=22),
        BenchmarkCase(name='macd_baseline', strategy_key='macd', seed=33),
        BenchmarkCase(name='breakout_baseline', strategy_key='breakout', seed=44),
    ]
    results = [run_case(case) for case in cases]
    return {
        'suite': 'backtest_framework_benchmark',
        'version': 1,
        'results': results,
    }


def main():
    payload = run_benchmark_suite()
    out = '/root/.openclaw/workspace/quant/quant/data/backtest_benchmark.json'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(out)
    for row in payload['results']:
        s = row['summary']
        print(f"{row['case']['name']}: ret={s['total_return_pct']:.2f}% dd={s['max_drawdown_pct']:.2f}% sharpe={s['sharpe_ratio']:.3f}")


if __name__ == '__main__':
    main()
