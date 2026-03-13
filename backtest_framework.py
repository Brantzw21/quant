#!/usr/bin/env python3
"""
策略回测框架
统一的回测接口，支持多策略
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import itertools
import json
import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    leverage: float = 1.0
    risk_free_rate: float = 0.02
    position_pct: float = 0.95
    symbol: str = "BTCUSDT"
    min_trade_value: float = 10.0
    maker_fee: float = 0.0002
    taker_fee: float = 0.0007
    use_maker_taker: bool = False


@dataclass
class Trade:
    """交易记录"""
    time: str
    symbol: str
    side: str
    price: float
    quantity: float
    value: float
    commission: float
    slippage: float
    pnl: float = 0.0
    fee_rate: float = 0.0
    trade_role: str = "taker"


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0.0

    @property
    def value(self) -> float:
        return self.quantity * self.current_price

    @property
    def pnl(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity


class Strategy(ABC):
    """策略基类"""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """返回 1=BUY, -1=SELL, 0=HOLD"""

    @abstractmethod
    def get_name(self) -> str:
        """返回策略名称"""


class Backtester:
    """统一回测框架"""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.strategy: Optional[Strategy] = None
        self.data: Optional[pd.DataFrame] = None
        self.reset()

    def set_strategy(self, strategy: Strategy):
        self.strategy = strategy

    def set_data(self, data: pd.DataFrame):
        self.data = data

    def reset(self):
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.equity_timestamps: List[str] = []
        self.stats: Dict = {}

    def run(self, data: Optional[pd.DataFrame] = None, strategy: Optional[Strategy] = None) -> Dict:
        if data is not None:
            self.data = data.copy()
        if strategy is not None:
            self.strategy = strategy

        if self.data is None or self.strategy is None:
            raise ValueError("data 和 strategy 不能为空")

        self.reset()
        df = self._prepare_data(self.data)
        signals = self.strategy.generate_signals(df).reindex(df.index).fillna(0)

        for i in range(len(df)):
            row = df.iloc[i]
            timestamp = self._row_timestamp(row.name, i)
            price = float(row['close'])

            for pos in self.positions.values():
                pos.current_price = price

            signal = int(signals.iloc[i])
            if signal == 1 and not self.positions:
                self._buy(timestamp, price)
            elif signal == -1 and self.positions:
                self._sell(timestamp, price)

            self.equity_curve.append(self._equity(price))
            self.equity_timestamps.append(timestamp)

        if self.positions:
            self._sell(self._row_timestamp(df.index[-1], len(df) - 1), float(df.iloc[-1]['close']))
            self.equity_curve[-1] = self._equity(float(df.iloc[-1]['close']))

        self.stats = self._calculate_stats()
        return self.stats

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        required = ['close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")

        if 'open' not in df.columns:
            df['open'] = df['close']
        if 'high' not in df.columns:
            df['high'] = df[['open', 'close']].max(axis=1)
        if 'low' not in df.columns:
            df['low'] = df[['open', 'close']].min(axis=1)
        if 'volume' not in df.columns:
            df['volume'] = 0.0

        return df

    def _row_timestamp(self, row_name, idx: int) -> str:
        if hasattr(row_name, 'strftime'):
            return row_name.strftime('%Y-%m-%d %H:%M:%S')
        return str(idx)

    def _equity(self, current_price: float) -> float:
        return self.cash + sum(pos.quantity * current_price for pos in self.positions.values())

    def _fee_rate(self, trade_role: str) -> float:
        if self.config.use_maker_taker:
            return self.config.maker_fee if trade_role == 'maker' else self.config.taker_fee
        return self.config.commission

    def _buy(self, timestamp: str, price: float, trade_role: str = 'taker'):
        fee_rate = self._fee_rate(trade_role)
        exec_price = price * (1 + self.config.slippage)
        deployable_cash = self.cash * min(self.config.position_pct, 1.0)
        quantity = max(deployable_cash * self.config.leverage / exec_price, 0)

        if quantity <= 0:
            return

        trade_value = quantity * exec_price
        commission = trade_value * fee_rate
        total_cost = trade_value + commission

        if total_cost > self.cash:
            quantity = self.cash / (exec_price * (1 + fee_rate))
            trade_value = quantity * exec_price
            commission = trade_value * fee_rate
            total_cost = trade_value + commission

        if quantity <= 0 or trade_value < self.config.min_trade_value:
            return

        self.cash -= total_cost
        self.positions[self.config.symbol] = Position(
            symbol=self.config.symbol,
            quantity=quantity,
            avg_price=exec_price,
            current_price=price,
        )
        self.trades.append(Trade(
            time=timestamp,
            symbol=self.config.symbol,
            side='BUY',
            price=exec_price,
            quantity=quantity,
            value=trade_value,
            commission=commission,
            slippage=exec_price - price,
            fee_rate=fee_rate,
            trade_role=trade_role,
        ))

    def _sell(self, timestamp: str, price: float, trade_role: str = 'maker'):
        pos = self.positions.get(self.config.symbol)
        if not pos:
            return

        fee_rate = self._fee_rate(trade_role)
        exec_price = price * (1 - self.config.slippage)
        gross_value = pos.quantity * exec_price
        commission = gross_value * fee_rate
        net_value = gross_value - commission
        pnl = net_value - (pos.quantity * pos.avg_price)

        if gross_value < self.config.min_trade_value:
            return

        self.cash += net_value
        self.trades.append(Trade(
            time=timestamp,
            symbol=self.config.symbol,
            side='SELL',
            price=exec_price,
            quantity=pos.quantity,
            value=net_value,
            commission=commission,
            slippage=price - exec_price,
            pnl=pnl,
            fee_rate=fee_rate,
            trade_role=trade_role,
        ))
        del self.positions[self.config.symbol]

    def _calculate_stats(self) -> Dict:
        if not self.equity_curve:
            return {}

        equity = np.array(self.equity_curve, dtype=float)
        returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([])
        returns = returns[~np.isnan(returns)]

        initial = float(self.config.initial_capital)
        final = float(equity[-1])
        total_return = (final - initial) / initial if initial else 0.0

        periods = max(len(equity), 1)
        annualized_return = (1 + total_return) ** (252 / periods) - 1 if periods > 1 and final > 0 else total_return
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        sharpe = (annualized_return - self.config.risk_free_rate) / volatility if volatility > 0 else 0.0

        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(float(np.min(drawdown))) if len(drawdown) else 0.0

        sell_trades = [t for t in self.trades if t.side == 'SELL']
        wins = [t for t in sell_trades if t.pnl > 0]
        losses = [t for t in sell_trades if t.pnl <= 0]
        total_commission = float(sum(t.commission for t in self.trades))
        total_slippage = float(sum(abs(t.slippage) * t.quantity for t in self.trades))
        profit_factor = (sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses))) if losses and sum(t.pnl for t in losses) != 0 else 0.0

        return {
            'strategy': self.strategy.get_name(),
            'symbol': self.config.symbol,
            'initial_capital': initial,
            'final_equity': final,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'total_trades': len(self.trades),
            'buy_trades': len([t for t in self.trades if t.side == 'BUY']),
            'sell_trades': len(sell_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(sell_trades) if sell_trades else 0.0,
            'total_commission': total_commission,
            'total_slippage_cost': total_slippage,
            'equity_curve': equity.tolist(),
            'equity_timestamps': self.equity_timestamps,
            'trades': [t.__dict__ for t in self.trades],
        }

    def save_results(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        payload = self.stats or self._calculate_stats()
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    def walk_forward(self, data: pd.DataFrame, strategy: Strategy, train_size: int, test_size: int, step_size: Optional[int] = None) -> Dict:
        """滚动窗口 walk-forward 回测。"""
        if train_size <= 0 or test_size <= 0:
            raise ValueError('train_size 和 test_size 必须大于 0')

        df = self._prepare_data(data)
        step = step_size or test_size
        windows = []

        start = 0
        while start + train_size + test_size <= len(df):
            train_df = df.iloc[start:start + train_size].copy()
            test_df = df.iloc[start + train_size:start + train_size + test_size].copy()
            result = self.run(test_df, strategy)
            windows.append({
                'train_start': start,
                'train_end': start + train_size - 1,
                'test_start': start + train_size,
                'test_end': start + train_size + test_size - 1,
                'result': result,
            })
            start += step

        aggregated_returns = [w['result']['total_return'] for w in windows if w.get('result')]
        aggregated_drawdowns = [w['result']['max_drawdown'] for w in windows if w.get('result')]
        aggregated_sharpes = [w['result']['sharpe_ratio'] for w in windows if w.get('result')]

        return {
            'windows': windows,
            'window_count': len(windows),
            'avg_total_return': float(np.mean(aggregated_returns)) if aggregated_returns else 0.0,
            'avg_max_drawdown': float(np.mean(aggregated_drawdowns)) if aggregated_drawdowns else 0.0,
            'avg_sharpe_ratio': float(np.mean(aggregated_sharpes)) if aggregated_sharpes else 0.0,
        }


class ParameterOptimizer:
    """基于统一回测框架的轻量参数优化器。"""

    def __init__(self, backtester: Backtester):
        self.backtester = backtester

    def grid_search(self, data: pd.DataFrame, strategy_cls, param_grid: Dict, config_builder=None, top_n: int = 10) -> List[Dict]:
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        results = []

        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            strategy = strategy_cls(**params)
            if config_builder:
                self.backtester.config = config_builder(params)
            result = self.backtester.run(data, strategy)
            results.append({
                'params': params,
                'total_return': result['total_return'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown'],
                'win_rate': result['win_rate'],
                'sell_trades': result['sell_trades'],
            })

        results.sort(key=lambda x: (x['sharpe_ratio'], x['total_return']), reverse=True)
        return results[:top_n]


if __name__ == '__main__':
    class RSIStrategy(Strategy):
        def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
            self.period = period
            self.overbought = overbought
            self.oversold = oversold

        def get_name(self) -> str:
            return f'RSI({self.period},{self.overbought},{self.oversold})'

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
    n = 200
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    data = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.uniform(1000, 5000, n),
    })

    backtester = Backtester(BacktestConfig(initial_capital=10000, symbol='BTCUSDT'))
    stats = backtester.run(data, RSIStrategy(14, 70, 30))
    print(f"总收益: {stats['total_return']:.2%}")
    print(f"最大回撤: {stats['max_drawdown']:.2%}")
    print(f"交易次数: {stats['sell_trades']}")
