#!/usr/bin/env python3
"""
绩效分析器
多维度绩效评估与归因分析
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Trade:
    """交易记录"""
    time: str
    symbol: str
    side: str  # BUY, SELL
    price: float
    quantity: float
    pnl: float = 0
    pnl_pct: float = 0


class PerformanceAnalyzer:
    """
    绩效分析器
    
    功能:
    - 基础指标计算
    - 风险调整收益
    - 交易统计
    - 归因分析
    - 滚动统计
    """
    
    def __init__(self, trades: List[Trade] = None):
        self.trades = trades or []
        
        # 如果有交易，计算收益序列
        self.returns = self._calculate_returns()
    
    def _calculate_returns(self) -> np.ndarray:
        """计算收益率序列"""
        if not self.trades:
            return np.array([])
        
        # 按时间排序
        sorted_trades = sorted(self.trades, key=lambda x: x.time)
        
        # 计算收益率
        returns = []
        for trade in sorted_trades:
            if trade.pnl_pct != 0:
                returns.append(trade.pnl_pct)
        
        return np.array(returns)
    
    # ===== 基础指标 =====
    
    def total_return(self) -> float:
        """总收益率"""
        if not self.returns.any():
            return 0
        return np.sum(self.returns)
    
    def annualized_return(self, periods_per_year: int = 252) -> float:
        """年化收益率"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        total = np.sum(self.returns)
        n = len(self.returns)
        
        # 年化
        return (1 + total) ** (periods_per_year / n) - 1
    
    def volatility(self, periods_per_year: int = 252) -> float:
        """年化波动率"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        return np.std(self.returns) * np.sqrt(periods_per_year)
    
    # ===== 风险指标 =====
    
    def sharpe_ratio(self, risk_free_rate: float = 0.02, periods_per_year: int = 252) -> float:
        """夏普比率"""
        vol = self.volatility(periods_per_year)
        
        if vol == 0:
            return 0
        
        return (self.annualized_return(periods_per_year) - risk_free_rate) / vol
    
    def sortino_ratio(self, risk_free_rate: float = 0.02, periods_per_year: int = 252) -> float:
        """索提诺比率 (只考虑下行波动)"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        # 下行波动率
        negative_returns = self.returns[self.returns < 0]
        
        if len(negative_returns) == 0:
            return float('inf')
        
        downside_vol = np.std(negative_returns) * np.sqrt(periods_per_year)
        
        if downside_vol == 0:
            return 0
        
        return (self.annualized_return(periods_per_year) - risk_free_rate) / downside_vol
    
    def max_drawdown(self) -> float:
        """最大回撤"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        # 累计收益
        cumulative = np.cumprod(1 + self.returns)
        
        # 历史高点
        peak = np.maximum.accumulate(cumulative)
        
        # 回撤
        drawdown = (cumulative - peak) / peak
        
        return abs(np.min(drawdown))
    
    def calmar_ratio(self, periods_per_year: int = 252) -> float:
        """卡尔玛比率 (年化收益/最大回撤)"""
        mdd = self.max_drawdown()
        
        if mdd == 0:
            return 0
        
        return self.annualized_return(periods_per_year) / mdd
    
    def var(self, confidence: float = 0.95) -> float:
        """VaR (Value at Risk)"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        return np.percentile(self.returns, (1 - confidence) * 100)
    
    def cvar(self, confidence: float = 0.95) -> float:
        """CVaR (Conditional VaR) / Expected Shortfall"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        var = self.var(confidence)
        
        return np.mean(self.returns[self.returns <= var])
    
    # ===== 交易统计 =====
    
    def win_rate(self) -> float:
        """胜率"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        wins = np.sum(self.returns > 0)
        
        return wins / len(self.returns)
    
    def profit_factor(self) -> float:
        """盈利因子"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        gross_profit = np.sum(self.returns[self.returns > 0])
        gross_loss = abs(np.sum(self.returns[self.returns < 0]))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        
        return gross_profit / gross_loss
    
    def avg_win(self) -> float:
        """平均盈利"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        wins = self.returns[self.returns > 0]
        
        return np.mean(wins) if len(wins) > 0 else 0
    
    def avg_loss(self) -> float:
        """平均亏损"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        losses = self.returns[self.returns < 0]
        
        return np.mean(losses) if len(losses) > 0 else 0
    
    def expectancy(self) -> float:
        """交易期望"""
        if not self.returns.any() or len(self.returns) == 0:
            return 0
        
        win_rate = self.win_rate()
        avg_win = self.avg_win()
        avg_loss = self.abs_loss()
        
        return win_rate * avg_win - (1 - win_rate) * avg_loss
    
    def abs_loss(self) -> float:
        """平均亏损 (正值)"""
        return abs(self.avg_loss())
    
    def trade_count(self) -> int:
        """交易次数"""
        return len(self.returns)
    
    def win_count(self) -> int:
        """盈利次数"""
        return int(np.sum(self.returns > 0))
    
    def loss_count(self) -> int:
        """亏损次数"""
        return int(np.sum(self.returns < 0))
    
    # ===== 滚动统计 =====
    
    def rolling_sharpe(self, window: int = 20) -> List[float]:
        """滚动夏普比率"""
        if len(self.returns) < window:
            return []
        
        sharpes = []
        
        for i in range(window, len(self.returns) + 1):
            window_returns = self.returns[i-window:i]
            
            vol = np.std(window_returns)
            
            if vol == 0:
                sharpes.append(0)
            else:
                sharpe = np.mean(window_returns) / vol * np.sqrt(252)
                sharpes.append(sharpe)
        
        return sharpes
    
    def rolling_max_drawdown(self, window: int = 20) -> List[float]:
        """滚动最大回撤"""
        if len(self.returns) < window:
            return []
        
        dd = []
        
        for i in range(window, len(self.returns) + 1):
            window_returns = self.returns[i-window:i]
            cumulative = np.cumprod(1 + window_returns)
            peak = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - peak) / peak
            dd.append(abs(np.min(drawdown)))
        
        return dd
    
    # ===== 综合报告 =====
    
    def get_report(self) -> Dict:
        """生成完整绩效报告"""
        return {
            'summary': {
                'total_return': round(self.total_return(), 4),
                'annualized_return': round(self.annualized_return(), 4),
                'volatility': round(self.volatility(), 4),
            },
            'risk': {
                'sharpe_ratio': round(self.sharpe_ratio(), 3),
                'sortino_ratio': round(self.sortino_ratio(), 3),
                'max_drawdown': round(self.max_drawdown(), 4),
                'calmar_ratio': round(self.calmar_ratio(), 3),
                'var_95': round(self.var(0.95), 4),
                'cvar_95': round(self.cvar(0.95), 4),
            },
            'trading': {
                'trade_count': self.trade_count(),
                'win_count': self.win_count(),
                'loss_count': self.loss_count(),
                'win_rate': round(self.win_rate(), 4),
                'profit_factor': round(self.profit_factor(), 2),
                'avg_win': round(self.avg_win(), 4),
                'avg_loss': round(self.avg_loss(), 4),
                'expectancy': round(self.expectancy(), 4),
            }
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("绩效分析器")
    print("=" * 50)
    
    # 模拟交易数据
    trades = [
        Trade("2026-01-01", "BTC", "BUY", 45000, 0.1, pnl_pct=0.02),
        Trade("2026-01-05", "BTC", "SELL", 45900, 0.1, pnl_pct=0.02),
        Trade("2026-01-10", "BTC", "BUY", 46000, 0.1, pnl_pct=-0.015),
        Trade("2026-01-15", "BTC", "SELL", 45310, 0.1, pnl_pct=-0.015),
        Trade("2026-01-20", "BTC", "BUY", 45000, 0.1, pnl_pct=0.03),
        Trade("2026-01-25", "BTC", "SELL", 46350, 0.1, pnl_pct=0.03),
    ]
    
    # 创建分析器
    analyzer = PerformanceAnalyzer(trades)
    
    # 生成报告
    report = analyzer.get_report()
    
    print("\n📊 绩效报告:")
    print(json.dumps(report, indent=2))
