"""
回测引擎
"""

import numpy as np


def run_backtest(data, signal_func, params, initial_capital=100000):
    """
    运行回测
    
    参数:
        data: 数据列表
        signal_func: 信号函数
        params: 策略参数
        initial_capital: 初始资金
    
    返回:
        回测结果字典
    """
    cash = initial_capital
    position = 0
    trades = []
    equity_curve = []
    dates = []
    
    for i, day in enumerate(data):
        current_data = data[:i+1]
        signal_result = signal_func(current_data, params)
        
        if isinstance(signal_result, tuple):
            signal, position_size = signal_result
        else:
            signal = signal_result
            position_size = 1.0
        
        price = float(day["close"])
        date = day["date"]
        
        if signal == "BUY" and position == 0 and cash >= price:
            actual_size = min(position_size, 1.0)
            shares = (cash * 0.95 * actual_size) / price
            cash -= shares * price
            position = shares
            trades.append({"date": date, "action": "BUY", "price": price, "size": actual_size})
        
        elif signal == "SELL" and position > 0:
            cash += position * price
            trades.append({"date": date, "action": "SELL", "price": price, "size": 1.0})
            position = 0
        
        equity = cash + position * price
        equity_curve.append(equity)
        dates.append(date)
    
    if position > 0:
        cash += position * float(data[-1]["close"])
    
    equity_curve.append(cash)
    dates.append(data[-1]["date"])
    
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    
    returns_list = []
    for i in range(1, len(equity_curve)):
        daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
        returns_list.append(daily_return)
    
    sharpe = (np.mean(returns_list) / np.std(returns_list)) * np.sqrt(252) if returns_list and np.std(returns_list) > 0 else 0
    
    peak = equity_curve[0]
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd
    
    days = len(data)
    years = days / 252
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "trades": len(trades) // 2,
        "equity_curve": equity_curve,
        "dates": dates,
        "final_equity": final_equity
    }


def run_dca_backtest(data, initial_capital=100000, dca_pct=0.01):
    """
    定投专用回测
    每月固定投入当前可用资金的dca_pct比例（按实际金额，不限制整手）
    """
    cash = initial_capital
    position = 0
    trades = []
    equity_curve = []
    dates = []
    
    for i, day in enumerate(data):
        current_date = day["date"]
        price = float(day["close"])
        
        if i > 0:
            prev_date = data[i-1]["date"]
            current_month = current_date[:7]
            prev_month = prev_date[:7]
            
            if current_month != prev_month:
                available = cash + position * price
                buy_amount = available * dca_pct
                if buy_amount > 0:
                    shares = buy_amount / price
                    cost = shares * price
                    cash -= cost
                    position += shares
                    trades.append({"date": current_date, "action": "BUY", "price": price, "shares": shares, "amount": cost})
        
        equity = cash + position * price
        equity_curve.append(equity)
        dates.append(current_date)
    
    if position > 0:
        cash += position * float(data[-1]["close"])
    
    equity_curve.append(cash)
    dates.append(data[-1]["date"])
    
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    
    returns_list = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns_list.append(daily_return)
    
    sharpe = (np.mean(returns_list) / np.std(returns_list)) * np.sqrt(252) if returns_list and np.std(returns_list) > 0 else 0
    
    peak = equity_curve[0]
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd
    
    days = len(data)
    years = days / 252
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "trades": len(trades),
        "equity_curve": equity_curve,
        "dates": dates,
        "final_equity": final_equity
    }


def optimize_strategy(data, signal_func, param_grid, name):
    """
    参数优化 - 网格搜索
    """
    from itertools import product
    
    print(f"\n优化 {name}...")
    
    best_result = None
    best_score = -999
    best_params = None
    
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    total_combos = 1
    for v in values:
        total_combos *= len(v)
    print(f"  共 {total_combos} 种参数组合...")
    
    for combo in product(*values):
        params = dict(zip(keys, combo))
        result = run_backtest(data, signal_func, params)
        score = result['annual_return'] - 0.5 * result['max_drawdown']
        
        if score > best_score:
            best_score = score
            best_result = result
            best_params = params.copy()
    
    print(f"  最优参数: {best_params}")
    print(f"  年化收益: {best_result['annual_return']:.2%}")
    print(f"  最大回撤: {best_result['max_drawdown']:.2%}")
    print(f"  交易次数: {best_result['trades']}")
    print(f"  最终资金: {best_result['final_equity']:,.0f}")
    
    return best_result, best_params
