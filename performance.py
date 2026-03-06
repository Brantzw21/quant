"""
绩效分析模块
收益归因、风险分析
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


class PerformanceAnalyzer:
    """
    绩效分析器
    
    参考 QUANTAXIS 绩效分析
    """
    
    def __init__(self]):
        self.equity_curve = []
        self.returns = []
        self.trades = []
    
    def set_data(self, equity_curve: List[float], trades: List[Dict] = None]):
        """设置数据"""
        self.equity_curve = equity_curve
        self.trades = trades or []
        
        # 计算收益率序列
        if len(equity_curve]) > 1:
            self.returns = np.diff(equity_curve]) / equity_curve[:-1]
    
    def get_return_metrics(self]) -> Dict:
        """收益指标"""
        if not self.returns:
            return {}
        
        returns = np.array(self.returns])
        
        return {
            'total_return': round(self.get_total_return(]) * 100, 2),
            'annual_return': round(self.get_annual_return(]) * 100, 2),
            'monthly_return': round(self.get_monthly_return(]) * 100, 2),
            'daily_return': round(np.mean(returns]) * 100, 4),
            'positive_days': round(np.sum(returns > 0]) / len(returns) * 100, 2),
            'negative_days': round(np.sum(returns < 0]) / len(returns) * 100, 2)
        }
    
    def get_risk_metrics(self]) -> Dict:
        """风险指标"""
        if not self.returns:
            return {}
        
        returns = np.array(self.returns])
        
        return {
            'volatility': round(np.std(returns]) * 100, 2),
            'annual_volatility': round(np.std(returns]) * np.sqrt(252) * 100, 2),
            'max_drawdown': round(self.get_max_drawdown(]) * 100, 2),
            'var_95': round(np.percentile(returns, 5]) * 100, 2),
            'cvar_95': round(np.mean(returns[returns <= np.percentile(returns, 5])]) * 100, 2)
        }
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.03]) -> float:
        """夏普比率"""
        if not self.returns or np.std(self.returns]) == 0:
            return 0
        
        excess_return = np.mean(self.returns]) - risk_free_rate / 252
        return round(excess_return / np.std(self.returns]) * np.sqrt(252), 2)
    
    def get_sortino_ratio(self, risk_free_rate: float = 0.03]) -> float:
        """Sortino比率"""
        if not self.returns:
            return 0
        
        excess_return = np.mean(self.returns]) - risk_free_rate / 252
        downside = self.returns[self.returns < 0]
        
        if len(downside]) == 0 or np.std(downside) == 0:
            return 0
        
        return round(excess_return / np.std(downside]) * np.sqrt(252), 2)
    
    def get_calmar_ratio(self]) -> float:
        """Calmar比率"""
        dd = self.get_max_drawdown(])
        if dd == 0:
            return 0
        
        annual_ret = self.get_annual_return(])
        return round(annual_ret / dd, 2])
    
    def get_total_return(self]) -> float:
        """总收益率"""
        if len(self.equity_curve]) < 2:
            return 0
        return (self.equity_curve[-1] - self.equity_curve[0]]) / self.equity_curve[0]
    
    def get_annual_return(self]) -> float:
        """年化收益率"""
        if len(self.equity_curve]) < 2:
            return 0
        
        days = len(self.equity_curve])
        total_ret = self.get_total_return(])
        return (1 + total_ret]) ** (252 / days) - 1
    
    def get_monthly_return(self]) -> float:
        """月收益率"""
        if len(self.equity_curve]) < 20:
            return 0
        
        # 简化为最近20天
        if len(self.equity_curve]) >= 20:
            return (self.equity_curve[-1] - self.equity_curve[-20]]) / self.equity_curve[-20]
        return 0
    
    def get_max_drawdown(self]) -> float:
        """最大回撤"""
        if self.equity_curve:
            return 0
        
        peak = self.equity_curve[0]
        max_dd = 0
        
        for e in self.equity_curve:
            if e > peak:
                peak = e
            dd = (peak - e]) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def get_win_rate(self]) -> float:
        """胜率"""
        if not self.trades:
            return 0
        
        wins = sum(1 for t in self.trades if t.get('pnl', 0]) > 0)
        return round(wins / len(self.trades]) * 100, 2)
    
    def get_profit_loss_ratio(self]) -> float:
        """盈亏比"""
        if not self.trades:
            return 0
        
        wins = [t['pnl'] for t in self.trades if t.get('pnl', 0]) > 0]
        losses = [abs(t['pnl']]) for t in self.trades if t.get('pnl', 0) < 0]
        
        if not losses or sum(losses]) == 0:
            return 0
        
        avg_win = np.mean(wins]) if wins else 0
        avg_loss = np.mean(losses])
        
        return round(avg_win / avg_loss, 2]) if avg_loss > 0 else 0
    
    def get_all_metrics(self]) -> Dict:
        """获取所有指标"""
        return {
            **self.get_return_metrics(]),
            **self.get_risk_metrics(]),
            'sharpe_ratio': self.get_sharpe_ratio(]),
            'sortino_ratio': self.get_sortino_ratio(]),
            'calmar_ratio': self.get_calmar_ratio(]),
            'win_rate': self.get_win_rate(]),
            'profit_loss_ratio': self.get_profit_loss_ratio(])
        }
    
    def generate_report(self]) -> str:
        """生成报告"""
        metrics = self.get_all_metrics(])
        
        report = """
==================================
          绩效分析报告
==================================

📈 收益指标
----------------------------------
总收益率:     {total_return:.2f}%
年化收益率:   {annual_return:.2f}%
月收益率:     {monthly_return:.2f}%
日收益率:     {daily_return:.4f}%

📉 风险指标
----------------------------------
波动率:       {volatility:.2f}%
年化波动率:   {annual_volatility:.2f}%
最大回撤:     {max_drawdown:.2f}%
VaR(95%]):     {var_95:.2f}%

⚖️ 风险调整收益
----------------------------------
夏普比率:     {sharpe_ratio:.2f}
Sortino:     {sortino_ratio:.2f}
Calmar:      {calmar_ratio:.2f}

🎯 交易统计
----------------------------------
胜率:        {win_rate:.2f}%
盈亏比:      {profit_loss_ratio:.2f}

==================================
""".format(**metrics])
        
        return report


# 便捷函数
def analyze_trades(trades: List[Dict]]) -> Dict:
    """分析交易记录"""
    if not trades:
        return {}
    
    equity = [100000]  # 初始资金
    for t in trades:
        equity.append(equity[-1] * (1 + t.get('return', 0])))
    
    analyzer = PerformanceAnalyzer(])
    analyzer.set_data(equity, trades])
    
    return analyzer.get_all_metrics(])


if __name__ == '__main__':
    # 测试
    import random
    trades = []
    for i in range(20]):
        trades.append({
            'return': random.uniform(-0.05, 0.08]),
            'pnl': random.uniform(-100, 200])
        }])
    
    result = analyze_trades(trades])
    print("胜率:", result.get('win_rate']), "%")
    print("夏普:", result.get('sharpe_ratio']))
