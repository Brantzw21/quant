import numpy as np
import pandas as pd

from backtest_framework import Backtester, BacktestConfig, Strategy, ParameterOptimizer


class DemoStrategy(Strategy):
    def __init__(self, buy_index=5, sell_index=20):
        self.buy_index = buy_index
        self.sell_index = sell_index

    def get_name(self) -> str:
        return 'demo'

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        if len(signals) > self.buy_index:
            signals.iloc[self.buy_index] = 1
        if len(signals) > self.sell_index:
            signals.iloc[self.sell_index] = -1
        return signals


def make_df(n=80):
    np.random.seed(7)
    prices = 100 * np.cumprod(1 + np.random.normal(0.001, 0.01, n))
    return pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, n),
    })


def test_backtester_runs_and_exports(tmp_path):
    df = make_df()
    bt = Backtester(BacktestConfig(initial_capital=10000, symbol='TEST'))
    result = bt.run(df, DemoStrategy())
    assert 'total_return' in result
    assert result['total_trades'] >= 2

    out = tmp_path / 'result.json'
    bt.save_results(str(out))
    assert out.exists()


def test_walk_forward_returns_windows():
    df = make_df(120)
    bt = Backtester(BacktestConfig(initial_capital=10000, symbol='TEST'))
    wf = bt.walk_forward(df, DemoStrategy(), train_size=40, test_size=20)
    assert wf['window_count'] > 0
    assert 'avg_total_return' in wf


def test_parameter_optimizer_grid_search():
    df = make_df(120)

    class TunableStrategy(Strategy):
        def __init__(self, buy_index=5, sell_index=20):
            self.buy_index = buy_index
            self.sell_index = sell_index

        def get_name(self) -> str:
            return 'tunable'

        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            signals = pd.Series(0, index=data.index)
            if len(signals) > self.buy_index:
                signals.iloc[self.buy_index] = 1
            if len(signals) > self.sell_index:
                signals.iloc[self.sell_index] = -1
            return signals

    optimizer = ParameterOptimizer(Backtester(BacktestConfig(initial_capital=10000, symbol='TEST')))
    top = optimizer.grid_search(
        df,
        TunableStrategy,
        {'buy_index': [5, 8], 'sell_index': [20, 25]},
        top_n=2,
    )
    assert len(top) == 2
    assert 'params' in top[0]
