#!/usr/bin/env python3
"""
组合优化器
基于均值方差、风险平价、最小方差的组合优化
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from scipy.optimize import minimize


@dataclass
class Asset:
    """资产"""
    symbol: str
    expected_return: float  # 预期收益率
    volatility: float       # 波动率
    correlation: Dict[str, float] = None  # 与其他资产的相关性
    
    def __post_init__(self):
        if self.correlation is None:
            self.correlation = {}


class PortfolioOptimizer:
    """
    组合优化器
    
    方法:
    - 均值方差 (Mean-Variance)
    - 最小方差 (Minimum Variance)
    - 最大夏普 (Maximum Sharpe)
    - 风险平价 (Risk Parity)
    """
    
    def __init__(self, assets: List[Asset], risk_free_rate: float = 0.02):
        self.assets = assets
        self.risk_free_rate = risk_free_rate
        
        # 构建协方差矩阵
        self.cov_matrix = self._build_cov_matrix()
        
        # 构建相关矩阵
        self.corr_matrix = self._build_corr_matrix()
    
    def _build_cov_matrix(self) -> np.ndarray:
        """构建协方差矩阵"""
        n = len(self.assets)
        cov = np.zeros((n, n))
        
        for i, a in enumerate(self.assets):
            for j, b in enumerate(self.assets):
                if i == j:
                    cov[i, j] = a.volatility ** 2
                else:
                    # 协方差 = 相关性 * sigma_i * sigma_j
                    corr = a.correlation.get(b.symbol, 0.3)  # 默认相关性0.3
                    cov[i, j] = corr * a.volatility * b.volatility
        
        return cov
    
    def _build_corr_matrix(self) -> np.ndarray:
        """构建相关矩阵"""
        n = len(self.assets)
        corr = np.zeros((n, n))
        
        for i, a in enumerate(self.assets):
            for j, b in enumerate(self.assets):
                if i == j:
                    corr[i, j] = 1.0
                else:
                    corr[i, j] = a.correlation.get(b.symbol, 0.3)
        
        return corr
    
    def portfolio_return(self, weights: np.ndarray) -> float:
        """组合收益率"""
        returns = np.array([a.expected_return for a in self.assets])
        return np.dot(weights, returns)
    
    def portfolio_volatility(self, weights: np.ndarray) -> float:
        """组合波动率"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def portfolio_sharpe(self, weights: np.ndarray) -> float:
        """组合夏普比率"""
        ret = self.portfolio_return(weights)
        vol = self.portfolio_volatility(weights)
        
        if vol == 0:
            return 0
        
        return (ret - self.risk_free_rate) / vol
    
    def optimize_min_variance(self) -> Dict:
        """
        最小方差组合
        """
        n = len(self.assets)
        
        # 目标函数: 组合方差
        def objective(w):
            return self.portfolio_volatility(w) ** 2
        
        # 约束: 权重和为1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # 边界: 权重在0-1之间
        bounds = tuple((0, 1) for _ in range(n))
        
        # 初始权重
        x0 = np.array([1/n] * n)
        
        # 优化
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        
        return {
            'method': 'Minimum Variance',
            'weights': {a.symbol: round(w, 4) for a, w in zip(self.assets, weights) if w > 0.001},
            'expected_return': round(self.portfolio_return(weights), 4),
            'volatility': round(self.portfolio_volatility(weights), 4),
            'sharpe': round(self.portfolio_sharpe(weights), 3)
        }
    
    def optimize_max_sharpe(self) -> Dict:
        """
        最大夏普组合
        """
        n = len(self.assets)
        
        # 目标函数: -夏普比率 (最小化)
        def objective(w):
            return -self.portfolio_sharpe(w)
        
        # 约束
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # 边界
        bounds = tuple((0, 1) for _ in range(n))
        
        # 初始权重
        x0 = np.array([1/n] * n)
        
        # 优化
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        
        return {
            'method': 'Maximum Sharpe',
                        'weights': {a.symbol: round(w, 4) for a, w in zip(self.assets, weights) if w > 0.001},
            'expected_return': round(self.portfolio_return(weights), 4),
            'volatility': round(self.portfolio_volatility(weights), 4),
            'sharpe': round(self.portfolio_sharpe(weights), 3)
        }
    
    def optimize_mean_variance(self, target_return: float = None) -> Dict:
        """
        均值方差组合
        """
        n = len(self.assets)
        
        # 目标函数: 组合方差
        def objective(w):
            return self.portfolio_volatility(w) ** 2
        
        # 约束
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
        ]
        
        if target_return:
            constraints.append({
                'type': 'eq', 
                'fun': lambda w: self.portfolio_return(w) - target_return
            })
        
        # 边界
        bounds = tuple((0, 1) for _ in range(n))
        
        # 初始权重
        x0 = np.array([1/n] * n)
        
        # 优化
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        
        return {
            'method': 'Mean-Variance',
            'weights': {a.symbol: round(w, 4) for a, w in zip(self.assets, weights) if w > 0.001},
            'expected_return': round(self.portfolio_return(weights), 4),
            'volatility': round(self.portfolio_volatility(weights), 4),
            'sharpe': round(self.portfolio_sharpe(weights), 3)
        }
    
    def optimize_risk_parity(self) -> Dict:
        """
        风险平价组合
        每个资产的边际风险贡献相等
        """
        n = len(self.assets)
        
        # 目标函数: 风险贡献方差
        def objective(w):
            vol = self.portfolio_volatility(w)
            risk_contrib = w * (self.cov_matrix @ w) / vol
            target_risk = vol / n
            return np.sum((risk_contrib - target_risk) ** 2)
        
        # 约束
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # 边界
        bounds = tuple((0, 1) for _ in range(n))
        
        # 初始权重
        x0 = np.array([1/n] * n)
        
        # 优化
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        
        return {
            'method': 'Risk Parity',
            'weights': {a.symbol: round(w, 4) for a, w in zip(self.assets, weights) if w > 0.001},
            'expected_return': round(self.portfolio_return(weights), 4),
            'volatility': round(self.portfolio_volatility(weights), 4),
            'sharpe': round(self.portfolio_sharpe(weights), 3)
        }
    
    def get_efficient_frontier(self, n_points: int = 20) -> pd.DataFrame:
        """获取有效前沿"""
        # 获取收益率范围
        returns = [a.expected_return for a in self.assets]
        min_return = min(returns)
        max_return = max(returns)
        
        results = []
        
        for target in np.linspace(min_return, max_return, n_points):
            try:
                opt = self.optimize_mean_variance(target_return=target)
                results.append(opt)
            except:
                pass
        
        df = pd.DataFrame(results)
        
        return df
    
    def optimize_all(self) -> Dict:
        """获取所有优化方法的结果"""
        return {
            'min_variance': self.optimize_min_variance(),
            'max_sharpe': self.optimize_max_sharpe(),
            'risk_parity': self.optimize_risk_parity(),
            'equal_weight': self._equal_weight(),
            'efficient_frontier': self.get_efficient_frontier().to_dict('records')
        }
    
    def _equal_weight(self) -> Dict:
        """等权组合"""
        n = len(self.assets)
        weights = np.array([1/n] * n)
        
        return {
            'method': 'Equal Weight',
            'weights': {a.symbol: round(1/n, 4) for a in self.assets},
            'expected_return': round(self.portfolio_return(weights), 4),
            'volatility': round(self.portfolio_volatility(weights), 4),
            'sharpe': round(self.portfolio_sharpe(weights), 3)
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("组合优化器")
    print("=" * 50)
    
    # 定义资产
    assets = [
        Asset("BTC", expected_return=0.30, volatility=0.80, correlation={"ETH": 0.6}),
        Asset("ETH", expected_return=0.20, volatility=0.60, correlation={"BTC": 0.6}),
        Asset("SPY", expected_return=0.10, volatility=0.15, correlation={"BTC": 0.1, "ETH": 0.1}),
        Asset("GLD", expected_return=0.05, volatility=0.10, correlation={"BTC": 0.0, "ETH": 0.0}),
    ]
    
    # 创建优化器
    optimizer = PortfolioOptimizer(assets, risk_free_rate=0.02)
    
    # 优化
    print("\n📊 最小方差组合:")
    mv = optimizer.optimize_min_variance()
    print(f"  权重: {mv['weights']}")
    print(f"  预期收益: {mv['expected_return']:.1%}")
    print(f"  波动率: {mv['volatility']:.1%}")
    print(f"  夏普比率: {mv['sharpe']:.2f}")
    
    print("\n📊 最大夏普组合:")
    ms = optimizer.optimize_max_sharpe()
    print(f"  权重: {ms['weights']}")
    print(f"  预期收益: {ms['expected_return']:.1%}")
    print(f"  波动率: {ms['volatility']:.1%}")
    print(f"  夏普比率: {ms['sharpe']:.2f}")
    
    print("\n📊 风险平价组合:")
    rp = optimizer.optimize_risk_parity()
    print(f"  权重: {rp['weights']}")
    print(f"  预期收益: {rp['expected_return']:.1%}")
    print(f"  波动率: {rp['volatility']:.1%}")
    print(f"  夏普比率: {rp['sharpe']:.2f}")
