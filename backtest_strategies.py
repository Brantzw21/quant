"""
四种策略回测沪深300 - 对比基准指数
过去1.5年的回测分析
"""

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# ========== 策略信号函数 ==========

def ma_cross_signal(data: List[Dict], params: Dict) -> str:
    """均线交叉策略"""
    fast = params.get('fast_ma', 5)
    slow = params.get('slow_ma', 20)

    if len(data) < slow + 1:
        return "HOLD"

    closes = [d["close"] for d in data]

    ma_fast = sum(closes[-fast:]) / fast
    ma_slow = sum(closes[-slow:]) / slow

    prev_ma_fast = sum(closes[-fast-1:-1]) / fast
    prev_ma_slow = sum(closes[-slow-1:-1]) / slow

    if prev_ma_fast <= prev_ma_slow and ma_fast > ma_slow:
        return "BUY"
    elif prev_ma_fast >= prev_ma_slow and ma_fast < ma_slow:
        return "SELL"

    return "HOLD"


def rsi_reversal_signal(data: List[Dict], params: Dict) -> str:
    """RSI均值回归策略"""
    period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)

    if len(data) < period + 1:
        return "HOLD"

    closes = [d["close"] for d in data]

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return "HOLD"

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if rsi < oversold:
        return "BUY"
    elif rsi > overbought:
        return "SELL"

    return "HOLD"


def breakout_signal(data: List[Dict], params: Dict) -> str:
    """突破策略"""
    lookback = params.get('lookback', 20)
    factor = params.get('breakout_factor', 1.02)

    if len(data) < lookback + 1:
        return "HOLD"

    closes = [d["close"] for d in data]
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]

    current_price = closes[-1]
    prev_price = closes[-2]

    recent_high = max(highs[-lookback:-1])
    recent_low = min(lows[-lookback:-1])

    if prev_price < recent_high * factor and current_price > recent_high * factor:
        return "BUY"
    elif prev_price > recent_low / factor and current_price < recent_low / factor:
        return "SELL"

    return "HOLD"


def dual_ma_rsi_signal(data: List[Dict], params: Dict) -> str:
    """双均线+RSI组合策略"""
    fast_ma = params.get('fast_ma', 10)
    slow_ma = params.get('slow_ma', 30)
    rsi_period = params.get('rsi_period', 14)
    rsi_thresh = params.get('rsi_threshold', 50)

    if len(data) < slow_ma + 1:
        return "HOLD"

    closes = [d["close"] for d in data]

    ma_fast = sum(closes[-fast_ma:]) / fast_ma
    ma_slow = sum(closes[-slow_ma:]) / slow_ma

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    if ma_fast > ma_slow and rsi > rsi_thresh:
        return "BUY"
    elif ma_fast < ma_slow or rsi < rsi_thresh:
        return "SELL"

    return "HOLD"


# ========== 回测引擎 ==========

def run_backtest(data: List[Dict], signal_func, params: Dict,
                 initial_capital: float = 100000) -> Dict:
    """运行回测"""
    cash = initial_capital
    position = 0
    trades = []
    equity_curve = []

    for i, day in enumerate(data):
        current_data = data[:i+1]
        signal = signal_func(current_data, params)
        price = day["close"]
        date = day["date"]

        if signal == "BUY" and position == 0 and cash > 0:
            shares = int(cash / price / 100) * 100
            if shares > 0:
                cost = shares * price
                cash -= cost
                position = shares
                trades.append({"date": date, "action": "BUY", "price": price, "shares": shares})

        elif signal == "SELL" and position > 0:
            proceeds = position * price
            cash += proceeds
            trades.append({"date": date, "action": "SELL", "price": price, "shares": position})
            position = 0

        equity = cash + position * price
        equity_curve.append({"date": date, "equity": equity})

    # 最后平仓
    if position > 0:
        final_price = data[-1]["close"]
        cash += position * final_price
        trades.append({"date": data[-1]["date"], "action": "SELL", "price": final_price, "shares": position})
        position = 0

    equity_curve.append({"date": data[-1]["date"], "equity": cash})

    # 计算指标
    equities = [e["equity"] for e in equity_curve]
    final_equity = equities[-1]
    total_return = (final_equity - initial_capital) / initial_capital

    # 年化收益
    days = len(data)
    years = days / 252
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    # 夏普比率
    returns = []
    for i in range(1, len(equities)):
        daily_return = (equities[i] - equities[i-1]) / equities[i-1]
        returns.append(daily_return)

    if returns and np.std(returns) > 0:
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
    else:
        sharpe = 0

    # 最大回撤
    peak = equities[0]
    max_dd = 0
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd

    # 胜率
    buy_trades = [t for t in trades if t["action"] == "BUY"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]

    wins = 0
    for i in range(min(len(buy_trades), len(sell_trades))):
        if sell_trades[i]["price"] > buy_trades[i]["price"]:
            wins += 1

    win_rate = wins / len(sell_trades) if sell_trades else 0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "trades": len(trades) // 2,
        "final_equity": final_equity
    }


# ========== 主程序 ==========

def main():
    print("=" * 70)
    print("四种策略回测 - 沪深300 过去1.5年")
    print("=" * 70)

    # 获取数据
    lg = bs.login()
    print(f"登录: {lg.error_msg}")

    index_code = "sh.000300"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=550)).strftime("%Y-%m-%d")

    print(f"回测区间: {start_date} ~ {end_date}")

    rs = bs.query_history_k_data_plus(
        index_code,
        "date,open,high,low,close,volume",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )

    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())

    bs.logout()

    df = pd.DataFrame(data_list, columns=rs.fields)
    df['close'] = pd.to_numeric(df['close'])

    # 基准指数买入持有收益
    index_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
    print(f"\n基准(买入持有)收益: {index_return:.2%}")
    print(f"交易天数: {len(df)} 天")

    # 准备数据
    data = df.to_dict('records')

    # 策略配置
    strategies = {
        "ma_cross": {
            "name": "均线交叉(MA5/MA20)",
            "func": ma_cross_signal,
            "params": {"fast_ma": 5, "slow_ma": 20}
        },
        "rsi_reversal": {
            "name": "RSI均值回归(14,30,70)",
            "func": rsi_reversal_signal,
            "params": {"rsi_period": 14, "oversold": 30, "overbought": 70}
        },
        "breakout": {
            "name": "突破策略(20日)",
            "func": breakout_signal,
            "params": {"lookback": 20, "breakout_factor": 1.02}
        },
        "dual_ma_rsi": {
            "name": "双均线+RSI组合",
            "func": dual_ma_rsi_signal,
            "params": {"fast_ma": 10, "slow_ma": 30, "rsi_period": 14, "rsi_threshold": 50}
        }
    }

    # 运行回测
    print("\n" + "=" * 70)
    print("回测结果")
    print("=" * 70)

    results = []

    for code, strat in strategies.items():
        result = run_backtest(data, strat["func"], strat["params"])
        result["name"] = strat["name"]
        result["code"] = code
        result["vs_index"] = result["total_return"] - index_return
        results.append(result)

    # 打印结果
    print(f"\n{'策略':<25} {'总收益':>10} {'年化':>10} {'夏普':>8} {'最大回撤':>10} {'交易次数':>8} {'跑赢指数':>10}")
    print("-" * 95)

    for r in results:
        print(f"{r['name']:<25} {r['total_return']:>9.2%} {r['annual_return']:>9.2%} {r['sharpe_ratio']:>7.2f} {r['max_drawdown']:>9.2%} {r['trades']:>8d} {r['vs_index']:>+9.2%}")

    print("-" * 95)
    print(f"{'沪深300(基准)':<25} {index_return:>9.2%} {'-':>10} {'-':>8} {'-':>10} {'-':>8} {'-':>10}")

    # 总结
    print("\n" + "=" * 70)
    print("跑赢指数排名")
    print("=" * 70)

    sorted_results = sorted(results, key=lambda x: x['vs_index'], reverse=True)

    for i, r in enumerate(sorted_results, 1):
        status = "✅ 跑赢" if r['vs_index'] > 0 else "❌ 跑输"
        print(f"{i}. {r['name']}: {r['vs_index']:+.2%} {status}")


if __name__ == "__main__":
    main()
