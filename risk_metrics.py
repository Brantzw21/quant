"""
风险指标计算模块
计算: 最大回撤、年化波动率、夏普比率、Calmar Ratio
"""
import numpy as np


def calculate_max_drawdown(equity_curve):
    """计算最大回撤"""
    if len(equity_curve) < 2:
        return 0
    
    peak = equity_curve[0]
    max_dd = 0
    
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    
    return max_dd * 100  # 百分比


def calculate_annual_volatility(returns, periods_per_year=365):
    """计算年化波动率"""
    if len(returns) < 2:
        return 0
    
    returns = np.array(returns)
    std = np.std(returns, ddof=1)
    return std * np.sqrt(periods_per_year) * 100  # 百分比


def calculate_sharpe_ratio(returns, risk_free_rate=0.03, periods_per_year=365):
    """计算夏普比率"""
    if len(returns) < 2:
        return 0
    
    returns = np.array(returns)
    excess_returns = returns - risk_free_rate / periods_per_year
    
    if np.std(returns) == 0:
        return 0
    
    return np.mean(excess_returns) / np.std(returns) * np.sqrt(periods_per_year)


def calculate_calmar_ratio(total_return, max_drawdown, years):
    """计算Calmar Ratio"""
    if max_drawdown == 0:
        return 0
    
    annualized_return = (total_return / years) if years > 0 else 0
    return annualized_return / (max_drawdown / 100)


def calculate_sortino_ratio(returns, risk_free_rate=0.03, periods_per_year=365):
    """计算Sortino比率 (只考虑下行风险)"""
    if len(returns) < 2:
        return 0
    
    returns = np.array(returns)
    excess_returns = returns - risk_free_rate / periods_per_year
    
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0 or np.std(downside_returns) == 0:
        return 0
    
    return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(periods_per_year)


def calculate_win_rate(trades):
    """计算胜率"""
    if len(trades) == 0:
        return 0
    
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return wins / len(trades) * 100


def calculate_profit_factor(trades):
    """计算盈利因子"""
    if len(trades) == 0:
        return 0
    
    gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
    gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0
    
    return gross_profit / gross_loss


def calculate_all_metrics(equity_curve, trades, initial_balance=10000):
    """计算所有风险指标"""
    if len(equity_curve) < 2:
        return {}
    
    # 计算收益率序列
    returns = []
    for i in range(1, len(equity_curve)):
        ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
        returns.append(ret)
    
    # 基础指标
    total_return = (equity_curve[-1] - initial_balance) / initial_balance * 100
    years = len(equity_curve) / 365
    
    return {
        'total_return': total_return,
        'annual_return': total_return / years if years > 0 else 0,
        'max_drawdown': calculate_max_drawdown(equity_curve),
        'annual_volatility': calculate_annual_volatility(returns),
        'sharpe_ratio': calculate_sharpe_ratio(returns),
        'sortino_ratio': calculate_sortino_ratio(returns),
        'calmar_ratio': calculate_calmar_ratio(total_return, calculate_max_drawdown(equity_curve), years),
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'total_trades': len(trades),
    }


if __name__ == '__main__':
    # 测试
    equity = [10000, 10500, 10200, 11000, 10800, 11500, 11200, 12000]
    trades = [
        {'pnl': 500},
        {'pnl': -300},
        {'pnl': 800},
        {'pnl': -200},
    ]
    
    metrics = calculate_all_metrics(equity, trades)
    for k, v in metrics.items():
        print(f"{k}: {v:.2f}")
