#!/usr/bin/env python3
"""
统一回测系统 - 基于 backtest_framework 的标准入口
支持多市场数据接入与多策略对比
"""

import os
import sys
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_framework import Backtester, BacktestConfig, Strategy
from data_manager import MarketDataManager, FuturesDataManager
from strategies.advanced_strategies import (
    momentum_signal,
    ma_cross_signal,
    macd_signal,
    turtle_signal,
    channel_breakout_signal,
)
from strategies.trend_breakout import trend_breakout_signal
from strategies.weekly_strategy import weekly_trend_signal


MARKETS = {
    "a_stock": {
        "name": "A股",
        "examples": ["sh.000300", "sz.399006", "sh.510300"],
    },
    "crypto": {
        "name": "加密货币",
        "examples": ["BTCUSDT", "ETHUSDT"],
    },
    "us_stock": {
        "name": "美股",
        "examples": ["AAPL", "MSFT", "GOOGL"],
    },
}


class FunctionStrategy(Strategy):
    """把旧 signal_func 适配到统一回测框架。"""

    def __init__(self, name: str, signal_func, params: Dict):
        self.name = name
        self.signal_func = signal_func
        self.params = params or {}

    def get_name(self) -> str:
        return self.name

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = []
        rows = data.to_dict("records")
        for i in range(len(rows)):
            if i < 50:
                signals.append(0)
                continue
            signal = self.signal_func(rows[: i + 1], self.params)
            if signal == "BUY":
                signals.append(1)
            elif signal == "SELL":
                signals.append(-1)
            else:
                signals.append(0)
        return pd.Series(signals, index=data.index)


STRATEGIES: Dict[str, Tuple[str, object, Dict]] = {
    "momentum": ("动量策略", momentum_signal, {"period": 20}),
    "ma_cross": ("均线交叉", ma_cross_signal, {"fast": 5, "slow": 20}),
    "macd": ("MACD", macd_signal, {}),
    "turtle": ("海龟策略", turtle_signal, {}),
    "breakout": ("趋势突破", trend_breakout_signal, {}),
    "channel": ("通道突破", channel_breakout_signal, {}),
    "weekly": ("周线策略", weekly_trend_signal, {}),
}


def get_data(market: str, symbol: str, start: str, end: str):
    dm = MarketDataManager()
    fdm = FuturesDataManager()

    if market == "a_stock":
        return dm.get_a_stock_klines(symbol, start, end)
    if market == "crypto":
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        since = int(start_dt.timestamp() * 1000)
        return fdm.get_futures_klines(symbol, "1d", since=since)
    if market == "us_stock":
        return dm.get_us_stock_klines(symbol, start, end)
    return None


def to_dataframe(raw_data) -> pd.DataFrame:
    if raw_data is None:
        return pd.DataFrame()

    if isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()
    else:
        df = pd.DataFrame(raw_data)

    rename_map = {
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
    }
    df = df.rename(columns=rename_map)

    required = ["open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            return pd.DataFrame()
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0.0
    else:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def run_backtest(
    market: str,
    symbol: str,
    start: str,
    end: str,
    strategy_key: str,
    initial_capital: float = 1000000,
) -> Dict:
    raw = get_data(market, symbol, start, end)
    df = to_dataframe(raw)
    if df.empty or len(df) < 60:
        return {"error": f"数据不足: {symbol}"}

    desc, func, params = STRATEGIES[strategy_key]
    strategy = FunctionStrategy(desc, func, params)
    config = BacktestConfig(initial_capital=initial_capital, symbol=symbol)
    backtester = Backtester(config)
    result = backtester.run(df, strategy)

    return {
        "market": market,
        "symbol": symbol,
        "strategy": strategy_key,
        "strategy_name": desc,
        "start": start,
        "end": end,
        **result,
    }


def compare_strategies(market: str, symbol: str, start: str, end: str, initial_capital: float = 1000000):
    print(f"\n{'=' * 60}")
    print(f"策略对比 - {symbol} ({start} ~ {end})")
    print(f"{'=' * 60}")

    results = []
    for key, (desc, _, _) in STRATEGIES.items():
        result = run_backtest(market, symbol, start, end, key, initial_capital)
        if result.get("error"):
            print(f"  {desc}: {result['error']}")
            continue
        results.append((desc, result))
        print(
            f"  {desc}: {result['total_return']:+.2%} "
            f"(交易{result['sell_trades']}次, 胜率{result['win_rate']:.0%}, 回撤{result['max_drawdown']:.2%})"
        )

    results.sort(key=lambda x: x[1]["total_return"], reverse=True)
    if results:
        print(f"\n🏆 最佳策略: {results[0][0]}")
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="统一回测系统")
    parser.add_argument("--market", "-m", default="a_stock", choices=["a_stock", "crypto", "us_stock"])
    parser.add_argument("--symbol", "-s", default="sz.399006")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-01-06")
    parser.add_argument("--capital", type=float, default=1000000)
    parser.add_argument("--strategy", default="momentum", choices=list(STRATEGIES.keys()))
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare_strategies(args.market, args.symbol, args.start, args.end, args.capital)
        return

    result = run_backtest(args.market, args.symbol, args.start, args.end, args.strategy, args.capital)
    if result.get("error"):
        print(result["error"])
        return

    print(f"{'=' * 60}")
    print(f"回测: {args.symbol}")
    print(f"市场: {args.market}, 策略: {result['strategy_name']}")
    print(f"时间: {args.start} ~ {args.end}")
    print(f"资金: {args.capital:,.0f}")
    print(f"{'=' * 60}")
    print(f"最终权益: {result['final_equity']:,.2f}")
    print(f"总收益: {result['total_return']:+.2%}")
    print(f"年化收益: {result['annualized_return']:+.2%}")
    print(f"最大回撤: {result['max_drawdown']:.2%}")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"卖出次数: {result['sell_trades']}")
    print(f"胜率: {result['win_rate']:.1%}")


if __name__ == "__main__":
    main()
