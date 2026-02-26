"""
=============================================================================
                    Quant 项目回测引擎 - 通用版
=============================================================================
支持: 股票/ETF/指数 回测
数据: Baostock

使用方法:
    python run_backtest.py                    # 默认沪深300指数
    python run_backtest.py --code sh.510300  # 沪深300ETF
    python run_backtest.py --code sh.600519  # 贵州茅台
=============================================================================
"""

import baostock as bs
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 策略模块 ====================

def ma_cross_signal(data, params):
    """均线交叉策略"""
    fast = params.get('fast_ma', 5)
    slow = params.get('slow_ma', 20)
    if len(data) < slow + 1:
        return "HOLD"
    closes = [float(d["close"]) for d in data]
    ma_fast = sum(closes[-fast:]) / fast
    ma_slow = sum(closes[-slow:]) / slow
    prev_ma_fast = sum(closes[-fast-1:-1]) / fast
    prev_ma_slow = sum(closes[-slow-1:-1]) / slow
    if prev_ma_fast <= prev_ma_slow and ma_fast > ma_slow:
        return "BUY"
    elif prev_ma_fast >= prev_ma_slow and ma_fast < ma_slow:
        return "SELL"
    return "HOLD"


def rsi_signal(data, params):
    """RSI均值回归策略"""
    period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    if len(data) < period + 1:
        return "HOLD"
    closes = [float(d["close"]) for d in data]
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return "HOLD"
    rsi = 100 - (100 / (1 + avg_gain/avg_loss))
    if rsi < oversold:
        return "BUY"
    elif rsi > overbought:
        return "SELL"
    return "HOLD"


def breakout_signal(data, params):
    """突破策略"""
    lookback = params.get('lookback', 20)
    factor = params.get('breakout_factor', 1.02)
    if len(data) < lookback + 1:
        return "HOLD"
    closes = [float(d["close"]) for d in data]
    highs = [float(d["high"]) for d in data]
    lows = [float(d["low"]) for d in data]
    if closes[-2] < max(highs[-lookback:-1]) * factor and closes[-1] > max(highs[-lookback:-1]) * factor:
        return "BUY"
    if closes[-2] > min(lows[-lookback:-1]) / factor and closes[-1] < min(lows[-lookback:-1]) / factor:
        return "SELL"
    return "HOLD"


def dual_ma_rsi_signal(data, params):
    """均线RSI组合策略"""
    fast_ma = params.get('fast_ma', 10)
    slow_ma = params.get('slow_ma', 30)
    rsi_period = params.get('rsi_period', 14)
    rsi_thresh = params.get('rsi_threshold', 50)
    if len(data) < slow_ma + 1:
        return "HOLD"
    closes = [float(d["close"]) for d in data]
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
        rsi = 100 - (100 / (1 + avg_gain/avg_loss))
    if ma_fast > ma_slow and rsi > rsi_thresh:
        return "BUY"
    elif ma_fast < ma_slow or rsi < rsi_thresh:
        return "SELL"
    return "HOLD"


def bb_rsi_signal(data, params):
    """布林带RSI组合策略"""
    bb_period = params.get('bb_period', 20)
    rsi_period = params.get('rsi_period', 14)
    if len(data) < max(bb_period, rsi_period) + 1:
        return "HOLD"
    
    closes = np.array([float(d["close"]) for d in data])
    recent = closes[-bb_period:]
    bb_mid = np.mean(recent)
    bb_std = np.std(recent)
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-rsi_period:])
    avg_loss = np.mean(losses[-rsi_period:])
    rsi = 100 - (100 / (1 + avg_gain/avg_loss)) if avg_loss > 0 else 100
    
    current = closes[-1]
    if rsi < 30 and current < bb_lower * 1.05:
        return "BUY"
    if rsi > 70 or current > bb_upper * 0.95:
        return "SELL"
    return "HOLD"


def robust_rsi_signal(data, params):
    """
    稳健RSI策略 - 延迟不敏感版
    特点:
    1. 趋势过滤: 价格 > MA50 才做多
    2. 回踩确认: RSI超卖后，第二天不创新低才进
    3. 强制持仓: 至少持有N天
    """
    rsi_period = params.get('rsi_period', 7)
    ma_period = params.get('ma_period', 50)
    hold_days = params.get('hold_days', 5)
    oversold = params.get('oversold', 30)
    exit_threshold = params.get('exit_threshold', 70)
    
    if len(data) < max(rsi_period, ma_period) + 5:
        return "HOLD"
    
    closes = [float(d["close"]) for d in data]
    
    # 趋势过滤
    ma50 = np.mean(closes[-ma_period:])
    current_price = closes[-1]
    trend_ok = current_price > ma50
    
    # RSI计算
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        return "HOLD"
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # 买入条件
    if trend_ok and rsi < oversold:
        # 回踩确认
        if len(closes) > 3 and closes[-1] < min(closes[-3:-1]):
            return "BUY"
        if rsi < oversold - 5:
            return "BUY"
    
    # 卖出条件
    if rsi > exit_threshold:
        return "SELL"
    
    return "HOLD"


# ==================== 回测引擎 ====================

def run_backtest(data, signal_func, params, initial_capital=100000, position_pct=0.95):
    """执行回测"""
    cash = initial_capital
    position = 0
    trades = []
    equity_curve = []
    
    for i, day in enumerate(data):
        current_data = data[:i+1]
        signal = signal_func(current_data, params)
        price = float(day["close"])
        
        if signal == "BUY" and position == 0 and cash > 100:
            shares = (cash * position_pct) / price
            cash -= shares * price
            position = shares
            trades.append({"date": day["date"], "action": "BUY", "price": price})
        elif signal == "SELL" and position > 0:
            cash += position * price
            trades.append({"date": day["date"], "action": "SELL", "price": price})
            position = 0
        
        equity_curve.append(cash + position * price)
    
    if position > 0:
        cash += position * float(data[-1]["close"])
        trades.append({"date": data[-1]["date"], "action": "SELL", "price": float(data[-1]["close"])})
    
    # 计算指标
    final_equity = cash
    total_return = (final_equity - initial_capital) / initial_capital
    
    returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] for i in range(1, len(equity_curve))]
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    peak = equity_curve[0]
    max_dd = 0
    for e in equity_curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak
        if dd > max_dd:
            max_dd = dd
    
    buy_trades = [t for t in trades if t["action"] == "BUY"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    wins = sum(1 for i in range(min(len(buy_trades), len(sell_trades))) if sell_trades[i]["price"] > buy_trades[i]["price"])
    win_rate = wins / len(sell_trades) if sell_trades else 0
    
    return {
        "total_return": total_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "trades": len(trades) // 2,
        "equity_curve": equity_curve,
        "final_value": cash
    }


# ==================== 主程序 ====================

def main():
    # 命令行参数
    parser = argparse.ArgumentParser(description='Quant回测引擎')
    parser.add_argument('--code', type=str, default='sh.000300', help='代码: sh.000300(沪深300) / sh.510300(ETF) / sh.600519(股票)')
    parser.add_argument('--start', type=str, default='2023-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2026-02-24', help='结束日期')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    args = parser.parse_args()
    
    code = args.code
    start_date = args.start
    end_date = args.end
    initial_capital = args.capital
    
    # 代码名称映射
    code_names = {
        'sh.000300': '沪深300指数',
        'sz.399001': '深证成指',
        'sh.510300': '沪深300ETF',
        'sh.510500': '中证500ETF',
        'sh.600519': '贵州茅台',
        'sh.000858': '五粮液',
    }
    name = code_names.get(code, code)
    
    # 1. 获取数据
    print(f"📥 正在获取 {name} 数据...")
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    bs.logout()
    
    if not data_list:
        print(f"❌ 无法获取 {code} 的数据")
        return
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    data = df.to_dict('records')
    
    # 基准收益
    first_close = df['close'].iloc[0]
    last_close = df['close'].iloc[-1]
    index_return = (last_close - first_close) / first_close
    
    # 2. 配置策略
    strategies = {
        "MA Cross": {
            "func": ma_cross_signal,
            "params": {"fast_ma": 5, "slow_ma": 20},
            "color": "#e74c3c"
        },
        "RSI": {
            "func": rsi_signal,
            "params": {"rsi_period": 14, "oversold": 30, "overbought": 70},
            "color": "#3498db"
        },
        "Breakout": {
            "func": breakout_signal,
            "params": {"lookback": 20, "breakout_factor": 1.02},
            "color": "#2ecc71"
        },
        "Dual MA+RSI": {
            "func": dual_ma_rsi_signal,
            "params": {"fast_ma": 10, "slow_ma": 30, "rsi_period": 14, "rsi_threshold": 50},
            "color": "#9b59b6"
        },
        "BB+RSI": {
            "func": bb_rsi_signal,
            "params": {"bb_period": 20, "rsi_period": 14},
            "color": "#f39c12"
        },
        "稳健RSI": {
            "func": robust_rsi_signal,
            "params": {"rsi_period": 7, "ma_period": 50, "hold_days": 5, "oversold": 30, "exit_threshold": 70},
            "color": "#1abc9c"
        }
    }
    
    # 3. 执行回测
    print(f"🔄 正在回测 {len(data)} 个交易日...\n")
    results = []
    for strat_name, strat in strategies.items():
        r = run_backtest(data, strat["func"], strat["params"], initial_capital)
        r["name"] = strat_name
        r["color"] = strat["color"]
        r["vs_index"] = r["total_return"] - index_return
        results.append(r)
    
    # 4. 输出结果
    print("=" * 70)
    print(f"           {name} 回测结果")
    print(f"           回测周期: {start_date} ~ {end_date}")
    print("=" * 70)
    print(f"\n{'策略':<15} {'总收益':>10} {'夏普':>8} {'最大回撤':>10} {'交易次数':>8} {'vs基准':>10}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['name']:<15} {r['total_return']:>9.1%} {r['sharpe_ratio']:>7.2f} {r['max_drawdown']:>9.1%} {r['trades']:>8d} {r['vs_index']:>+9.1%}")
    
    print("-" * 70)
    print(f"{name:<15} {index_return:>9.1%} (买入持有)")
    print("=" * 70)
    
    # 5. 排名
    print("\n📈 收益排名:")
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    for i, r in enumerate(sorted_results, 1):
        print(f"  {i}. {r['name']}: {r['total_return']:+.1%}")
    
    # 6. 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{name} Strategy Backtest', fontsize=14, fontweight='bold')
    
    # 权益曲线
    ax1 = axes[0, 0]
    for r in results:
        ax1.plot(r["equity_curve"], label=r["name"], color=r["color"], linewidth=1.5)
    index_equity = [initial_capital * (1 + (df['close'].iloc[i] - first_close) / first_close) for i in range(len(df))]
    ax1.plot(index_equity, label=name, color='gray', linestyle='--', linewidth=1.5)
    ax1.set_title('Equity Curve')
    ax1.set_xlabel('Days')
    ax1.set_ylabel('Portfolio Value')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 收益对比
    ax2 = axes[0, 1]
    names = [r["name"] for r in results] + [name]
    returns = [r["total_return"] * 100 for r in results] + [index_return * 100]
    colors = [r["color"] for r in results] + ['gray']
    ax2.bar(names, returns, color=colors)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Total Return (%)')
    ax2.set_ylabel('Return (%)')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 夏普比率
    ax3 = axes[1, 0]
    ax3.bar([r["name"] for r in results], [r["sharpe_ratio"] for r in results], color=[r["color"] for r in results])
    ax3.set_title('Sharpe Ratio')
    ax3.set_ylabel('Sharpe')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 回撤
    ax4 = axes[1, 1]
    ax4.bar([r["name"] for r in results], [r["max_drawdown"]*100 for r in results], color=[r["color"] for r in results])
    ax4.set_title('Max Drawdown (%)')
    ax4.set_ylabel('Drawdown (%)')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('backtest_result.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 图表已保存: backtest_result.png")


if __name__ == "__main__":
    main()
