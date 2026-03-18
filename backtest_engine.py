#!/usr/bin/env python3
"""
回测引擎兼容层

说明：
- 当前项目默认主回测框架已切换到 backtest_framework.py
- 本文件保留旧名称，作为兼容入口，避免历史导入直接失效
"""

import sys
import os
from typing import Callable, Dict, Optional

import pandas as pd

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_framework import Backtester, BacktestConfig, Strategy
from backtest_models import Signal, Side, SignalType


class RiskManager:
    """兼容壳：旧调用最小保留，复杂风控请转到统一主框架。"""

    def __init__(self,
                 max_position_pct: float = 0.5,
                 max_daily_trades: int = 10,
                 max_drawdown_pct: float = 0.2,
                 atr_multiplier: float = 1.5):
        self.max_position_pct = max_position_pct
        self.max_daily_trades = max_daily_trades
        self.max_drawdown_pct = max_drawdown_pct
        self.atr_multiplier = atr_multiplier

    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return float(atr.iloc[-1]) if len(atr.dropna()) else 0.0

    def compute_stop_levels(self, price: float, atr: float, side: str) -> tuple:
        if side == 'LONG':
            return price - atr * self.atr_multiplier, price + atr * self.atr_multiplier * 2
        return price + atr * self.atr_multiplier, price - atr * self.atr_multiplier * 2


class StrategyAgent:
    """兼容旧 strategy_func 调用风格。"""

    def __init__(self, strategy_func: Optional[Callable] = None):
        self.strategy_func = strategy_func

    def generate_signal(self, data: pd.DataFrame) -> Dict:
        if not self.strategy_func:
            return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'no strategy'}
        signal = self.strategy_func(data)
        # 兼容转换
        if signal.get('signal') == 'BUY':
            return Signal(side=Side.LONG, confidence=signal.get('confidence', 0.7), 
                         signal_type=SignalType.ENTRY, reason=signal.get('reason', ''))
        elif signal.get('signal') == 'SELL':
            return Signal(side=Side.FLAT, confidence=signal.get('confidence', 0.7),
                         signal_type=SignalType.EXIT, reason=signal.get('reason', ''))
        return Signal(side=Side.FLAT, confidence=signal.get('confidence', 0.5),
                     signal_type=SignalType.HOLD, reason=signal.get('reason', ''))


class _CompatStrategy(Strategy):
    """兼容旧策略函数格式"""
    
    def __init__(self, strategy_agent: StrategyAgent):
        self.strategy_agent = strategy_agent

    def get_name(self) -> str:
        return 'compat_strategy'

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = []
        for i in range(len(data)):
            if i < 50:
                signals.append(Signal())
                continue
            signal = self.strategy_agent.generate_signal(data.iloc[: i + 1])
            signals.append(signal)
        return pd.Series(signals, index=data.index)


class BacktestEngine:
    """兼容入口：内部委托给 backtest_framework.Backtester。"""

    def __init__(self,
                 initial_cash: float = 100000,
                 commission: float = 0.0004,
                 slippage: float = 0.0005,
                 position_pct: float = 0.2):
        self.config = BacktestConfig(
            initial_capital=initial_cash,
            commission=commission,
            slippage=slippage,
            position_pct=position_pct,
        )
        self.backtester = Backtester(self.config)
        self.strategy_agent = StrategyAgent()
        self.risk_manager = RiskManager()
        self._last_report: Dict = {}
        self.trades = []
        self.equity_curve = []

    def set_strategy(self, strategy_func: Callable):
        self.strategy_agent.strategy_func = strategy_func

    def run(self, data: pd.DataFrame, use_atr: bool = True) -> Dict:
        strategy = _CompatStrategy(self.strategy_agent)
        report = self.backtester.run(data, strategy)
        report['use_atr'] = use_atr
        report['engine_mode'] = 'compat'
        self._last_report = report
        self.trades = report.get('trades', [])
        self.equity_curve = report.get('equity_curve', [])
        return report

    def get_report(self) -> Dict:
        return self._last_report

    def save_results(self, filename: str = 'backtest_results.json'):
        return self.backtester.save_results(filename)


if __name__ == '__main__':
    import numpy as np

    def sample_strategy(df: pd.DataFrame):
        close = df['close']
        ma10 = close.rolling(10).mean().iloc[-1]
        ma30 = close.rolling(30).mean().iloc[-1] if len(close) >= 30 else ma10
        if ma10 > ma30:
            return {'signal': 'BUY', 'confidence': 0.7}
        return {'signal': 'HOLD', 'confidence': 0.5}

    np.random.seed(42)
    n = 200
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    df = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.uniform(1000, 5000, n),
    })

    engine = BacktestEngine(initial_cash=10000)
    engine.set_strategy(sample_strategy)
    result = engine.run(df)
    print(f"总收益: {result['total_return']:.2%}")
    print("✅ 兼容层测试通过")
