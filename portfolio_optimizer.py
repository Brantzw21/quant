"""
组合优化器 - Portfolio Optimizer
=================================

功能:
- 多策略组合
- 权重优化
- 风险平价
- 均值方差优化

作者: AI量化系统
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """策略结果"""
    name: str
    returns: List[float]
    equity: List[float]
    trades: int


class PortfolioOptimizer:
    """
    组合优化器
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
    
    def equal_weight(self, strategies: List[StrategyResult]) -> Dict[str, float]:
        """等权组合"""
        n = len(strategies)
        return {s.name: 1.0/n for s in strategies}
    
    def risk_parity(self, strategies: List[StrategyResult]) -> Dict[str, float]:
        """
        风险平价组合
        
        原理: 各策略贡献相同风险
        """
        # 计算各策略波动率
        volatilities = {}
        for s in strategies:
            if len(s.returns) > 1:
                vol = np.std(s.returns) * np.sqrt(252)
            else:
                vol = 0.1
            volatilities[s.name] = vol
        
        # 波动率倒数作为权重
        total_inv_vol = sum(1/v for v in volatilities.values() if v > 0)
        
        weights = {}
        for name, vol in volatilities.items():
            if vol > 0:
                weights[name] = (1/vol) / total_inv_vol
            else:
                weights[name] = 0
        
        return weights
    
    def mean_variance(self, strategies: List[StrategyResult], 
                     target_return: float = None) -> Dict[str, float]:
        """
        均值方差优化 (Markowitz)
        
        原理: 最大化夏普比率
        """
        n = len(strategies)
        
        # 构建收益矩阵
        returns_matrix = np.array([s.returns for s in strategies])
        
        # 期望收益
        expected_returns = np.mean(returns_matrix, axis=1) * 252
        
        # 协方差矩阵
        cov_matrix = np.cov(returns_matrix) * 252
        
        # 简化: 用波动率倒数
        volatilities = np.array([np.std(s.returns) * np.sqrt(252) + 0.001 
                               for s in strategies])
        
        # 风险平价作为近似
        weights = 1 / volatilities
        weights = weights / np.sum(weights)
        
        return {s.name: w for s, w in zip(strategies, weights)}
    
    def momentum_weighted(self, strategies: List[StrategyResult], 
                       lookback: int = 60) -> Dict[str, float]:
        """
        动量加权
        
        原理: 近期表现好的权重高
        """
        weights = {}
        
        for s in strategies:
            if len(s.returns) >= lookback:
                # 近期收益
                recent = s.returns[-lookback:]
                momentum = np.mean(recent)
            else:
                momentum = 0
            
            # 用动量作为权重(正收益)
            weights[s.name] = max(0, momentum)
        
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        else:
            weights = self.equal_weight(strategies)
        
        return weights
    
    def inverse_vol_weighted(self, strategies: List[StrategyResult]) -> Dict[str, float]:
        """
        逆波动率加权
        
        原理: 波动率低的权重高
        """
        volatilities = {}
        
        for s in strategies:
            if len(s.returns) > 1:
                vol = np.std(s.returns) * np.sqrt(252)
            else:
                vol = 0.1
            volatilities[s.name] = vol
        
        # 逆波动率
        inv_vol = {k: 1/v for k, v in volatilities.items()}
        total = sum(inv_vol.values())
        
        weights = {k: v/total for k, v in inv_vol.items()}
        
        return weights
    
    def rank_weighted(self, strategies: List[StrategyResult]) -> Dict[str, float]:
        """
        排名加权
        
        原理: 按收益排名分配权重
        """
        # 计算各策略总收益
        total_returns = {s.name: sum(s.returns) for s in strategies}
        
        # 排序
        sorted_strategies = sorted(total_returns.items(), 
                                 key=lambda x: x[1], reverse=True)
        
        # 分配权重 (1/rank)
        weights = {}
        for i, (name, _) in enumerate(sorted_strategies):
            weights[name] = 1.0 / (i + 1)
        
        # 归一化
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    def optimize(self, strategies: List[StrategyResult], 
               method: str = "risk_parity") -> Dict[str, float]:
        """
        优化组合权重
        
        Args:
            strategies: 策略结果列表
            method: 优化方法
                - equal: 等权
                - risk_parity: 风险平价
                - mean_variance: 均值方差
                - momentum: 动量加权
                - inverse_vol: 逆波动率
                - rank: 排名加权
        
        Returns:
            {策略名: 权重}
        """
        methods = {
            "equal": self.equal_weight,
            "risk_parity": self.risk_parity,
            "mean_variance": self.mean_variance,
            "momentum": self.momentum_weighted,
            "inverse_vol": self.inverse_vol_weighted,
            "rank": self.rank_weighted,
        }
        
        if method not in methods:
            method = "risk_parity"
        
        return methods[method](strategies)
    
    def evaluate_portfolio(self, strategies: List[StrategyResult],
                          weights: Dict[str, float]) -> Dict:
        """
        评估组合表现
        """
        # 构建组合收益
        portfolio_returns = []
        
        # 获取最大长度
        max_len = max(len(s.returns) for s in strategies)
        
        for i in range(max_len):
            port_ret = 0
            for s in strategies:
                if i < len(s.returns):
                    port_ret += s.returns[i] * weights.get(s.name, 0)
            portfolio_returns.append(port_ret)
        
        # 计算指标
        total_return = sum(portfolio_returns)
        
        if len(portfolio_returns) > 1:
            returns_arr = np.array(portfolio_returns)
            volatility = np.std(returns_arr) * np.sqrt(252)
            sharpe = (total_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # 最大回撤
            equity = [1]
            for r in portfolio_returns:
                equity.append(equity[-1] * (1 + r))
            
            peak = equity[0]
            max_dd = 0
            for e in equity:
                if e > peak: peak = e
                dd = (peak - e) / peak
                if dd > max_dd: max_dd = dd
        else:
            volatility = 0
            sharpe = 0
            max_dd = 0
        
        return {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'weights': weights
        }


def compute_correlation(strategies: List[StrategyResult]) -> pd.DataFrame:
    """
    计算策略相关性矩阵
    """
    returns_dict = {}
    
    for s in strategies:
        returns_dict[s.name] = s.returns
    
    # 转为DataFrame
    df = pd.DataFrame(returns_dict)
    
    # 计算相关性
    corr = df.corr()
    
    return corr


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 模拟策略结果
    strategies = []
    for name in ['策略A', '策略B', '策略C']:
        returns = [random.uniform(-0.02, 0.03) for _ in range(100)]
        equity = [100000]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        
        strategies.append(StrategyResult(
            name=name,
            returns=returns,
            equity=equity[1:],
            trades=random.randint(10, 30)
        ))
    
    # 优化
    optimizer = PortfolioOptimizer()
    
    print("组合优化结果:")
    print("-" * 50)
    
    for method in ['equal', 'risk_parity', 'inverse_vol', 'rank']:
        weights = optimizer.optimize(strategies, method)
        result = optimizer.evaluate_portfolio(strategies, weights)
        
        print(f"\n{method}:")
        print(f"  权重: {weights}")
        print(f"  收益: {result['total_return']:.2%}")
        print(f"  夏普: {result['sharpe_ratio']:.2f}")
        print(f"  回撤: {result['max_drawdown']:.2%}")
