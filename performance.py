#!/usr/bin/env python3
"""
绩效分析模块
参考 QUANTAXIS 绩效分析
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from typing import List, Dict, Optional
import numpy as np
import pandas as pd


class Performance:
    """绩效分析类"""
    
    def __init__(self):
        self.equity_curve = []
        self.returns = []
        self.trades = []
    
    def set_data(self, equity_curve: List[float], trades: List[Dict] = None):
        """设置数据"""
        self.equity_curve = equity_curve
        self.trades = trades or []
        
        # 计算收益率序列
        if len(equity_curve) > 1:
            self.returns = np.diff(equity_curve) / equity_curve[:-1]
    
    def get_return_metrics(self) -> Dict:
        """收益指标"""
        if not self.returns:
            return {}
        
        returns = np.array(self.returns)
        
        return {
            'total_return': round(self.get_total_return() * 100, 2),
            'annual_return': round(self.get_annual_return() * 100, 2),
            'monthly_return': round(self.get_monthly_return() * 100, 2),
            'daily_return': round(np.mean(returns) * 100, 4),
            'positive_days': round(np.sum(returns > 0) / len(returns) * 100, 2),
            'negative_days': round(np.sum(returns < 0) / len(returns) * 100, 2)
        }
    
    def get_risk_metrics(self) -> Dict:
        """风险指标"""
        if not self.returns:
            return {}
        
        returns = np.array(self.returns)
        
        return {
            'volatility': round(np.std(returns) * 100, 2),
            'annual_volatility': round(np.std(returns) * np.sqrt(252) * 100, 2),
            'max_drawdown': round(self.get_max_drawdown() * 100, 2),
            'sharpe_ratio': round(self.get_sharpe_ratio(), 2),
            'sortino_ratio': round(self.get_sortino_ratio(), 2)
        }
    
    def get_total_return(self) -> float:
        """总收益率"""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0
        return (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0]
    
    def get_annual_return(self) -> float:
        """年化收益率"""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0
        total = self.get_total_return()
        n_years = len(self.equity_curve) / 252
        return (1 + total) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    def get_monthly_return(self) -> float:
        """月化收益率"""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0
        total = self.get_total_return()
        n_months = len(self.equity_curve) / 21
        return (1 + total) ** (1 / n_months) - 1 if n_months > 0 else 0
    
    def get_max_drawdown(self) -> float:
        """最大回撤"""
        if not self.equity_curve:
            return 0
        
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        return abs(np.min(drawdown))
    
    def get_sharpe_ratio(self, risk_free: float = 0.02) -> float:
        """夏普比率"""
        if not self.returns or len(self.returns) < 2:
            return 0
        
        returns = np.array(self.returns)
        volatility = np.std(returns) * np.sqrt(252)
        
        if volatility == 0:
            return 0
        
        return (self.get_annual_return() - risk_free) / volatility
    
    def get_sortino_ratio(self, risk_free: float = 0.02) -> float:
        """索提诺比率"""
        if not self.returns or len(self.returns) < 2:
            return 0
        
        returns = np.array(self.returns)
        downside = returns[returns < 0]
        
        if len(downside) == 0:
            return float('inf')
        
        downside_vol = np.std(downside) * np.sqrt(252)
        
        if downside_vol == 0:
            return 0
        
        return (self.get_annual_return() - risk_free) / downside_vol
    
    def get_all_metrics(self) -> Dict:
        """获取所有指标"""
        return {
            **self.get_return_metrics(),
            **self.get_risk_metrics()
        }


__all__ = ['Performance']
