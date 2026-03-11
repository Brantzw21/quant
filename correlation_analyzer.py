#!/usr/bin/env python3
"""
相关性分析器
分析资产相关性、构建相关性矩阵
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class CorrelationPair:
    """相关性对"""
    asset1: str
    asset2: str
    correlation: float
    period: int  # 天数


class CorrelationAnalyzer:
    """
    相关性分析器
    
    功能:
    - 计算收益率相关性
    - 构建相关矩阵
    - 滚动相关性
    - 聚类分析
    """
    
    def __init__(self):
        self.price_data = {}
        self.returns_data = {}
    
    def add_price_series(self, symbol: str, prices: List[float], timestamps: List[str] = None):
        """
        添加价格序列
        
        Args:
            symbol: 资产符号
            prices: 价格列表
            timestamps: 时间戳列表
        """
        df = pd.DataFrame({
            'price': prices,
            'timestamp': timestamps or range(len(prices))
        })
        
        self.price_data[symbol] = df
        
        # 计算收益率
        df['return'] = df['price'].pct_change()
        self.returns_data[symbol] = df['return'].dropna()
    
    def add_dataframe(self, df: pd.DataFrame, symbol_col: str = 'symbol', 
                     price_col: str = 'close', time_col: str = 'timestamp'):
        """从DataFrame添加数据"""
        for symbol in df[symbol_col].unique():
            symbol_data = df[df[symbol_col] == symbol].copy()
            symbol_data = symbol_data.sort_values(time_col)
            
            self.add_price_series(
                symbol, 
                symbol_data[price_col].tolist(),
                symbol_data[time_col].tolist() if time_col in symbol_data.columns else None
            )
    
    def calculate_correlation(self, asset1: str, asset2: str) -> float:
        """计算两个资产的相关性"""
        if asset1 not in self.returns_data or asset2 not in self.returns_data:
            return 0
        
        returns1 = self.returns_data[asset1]
        returns2 = self.returns_data[asset2]
        
        # 对齐
        min_len = min(len(returns1), len(returns2))
        
        if min_len < 10:
            return 0
        
        corr = returns1.iloc[:min_len].corr(returns2.iloc[:min_len])
        
        return corr if not pd.isna(corr) else 0
    
    def get_correlation_matrix(self) -> pd.DataFrame:
        """获取相关矩阵"""
        symbols = list(self.returns_data.keys())
        
        if not symbols:
            return pd.DataFrame()
        
        n = len(symbols)
        matrix = np.zeros((n, n))
        
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                if i == j:
                    matrix[i, j] = 1.0
                else:
                    matrix[i, j] = self.calculate_correlation(s1, s2)
        
        df = pd.DataFrame(matrix, index=symbols, columns=symbols)
        
        return df
    
    def get_rolling_correlation(self, asset1: str, asset2: str, window: int = 30) -> List[float]:
        """计算滚动相关性"""
        if asset1 not in self.returns_data or asset2 not in self.returns_data:
            return []
        
        returns1 = self.returns_data[asset1]
        returns2 = self.returns_data[asset2]
        
        min_len = min(len(returns1), len(returns2))
        
        if min_len < window:
            return []
        
        rolling_corr = []
        
        for i in range(window, min_len):
            r1 = returns1.iloc[i-window:i]
            r2 = returns2.iloc[i-window:i]
            
            corr = r1.corr(r2)
            rolling_corr.append(corr if not pd.isna(corr) else 0)
        
        return rolling_corr
    
    def find_low_correlation_pairs(self, threshold: float = 0.3) -> List[CorrelationPair]:
        """找出低相关性资产对 (用于分散投资)"""
        pairs = []
        
        symbols = list(self.returns_data.keys())
        
        for i, s1 in enumerate(symbols):
            for s2 in symbols[i+1:]:
                corr = self.calculate_correlation(s1, s2)
                
                if abs(corr) < threshold:
                    pairs.append(CorrelationPair(s1, s2, corr, len(self.returns_data[s1])))
        
        # 按相关性排序
        pairs.sort(key=lambda x: abs(x.correlation))
        
        return pairs
    
    def find_high_correlation_pairs(self, threshold: float = 0.7) -> List[CorrelationPair]:
        """找出高相关性资产对 (用于对冲)"""
        pairs = []
        
        symbols = list(self.returns_data.keys())
        
        for i, s1 in enumerate(symbols):
            for s2 in symbols[i+1:]:
                corr = self.calculate_correlation(s1, s2)
                
                if abs(corr) > threshold:
                    pairs.append(CorrelationPair(s1, s2, corr, len(self.returns_data[s1])))
        
        # 按相关性排序
        pairs.sort(key=lambda x: abs(x.correlation), reverse=True)
        
        return pairs
    
    def cluster_assets(self, n_clusters: int = 3) -> Dict[int, List[str]]:
        """简单聚类 (基于相关性)"""
        # 简化实现：按相关性分层
        symbols = list(self.returns_data.keys())
        
        if len(symbols) < n_clusters:
            return {i: [symbols[i]] for i in range(len(symbols))}
        
        # 计算平均相关性
        avg_corr = {}
        
        for s1 in symbols:
            corrs = []
            for s2 in symbols:
                if s1 != s2:
                    corrs.append(abs(self.calculate_correlation(s1, s2)))
            avg_corr[s1] = np.mean(corrs) if corrs else 0
        
        # 按平均相关性排序并分组
        sorted_symbols = sorted(avg_corr.keys(), key=lambda x: avg_corr[x])
        
        clusters = {}
        cluster_size = len(sorted_symbols) // n_clusters
        
        for i in range(n_clusters):
            start = i * cluster_size
            end = start + cluster_size if i < n_clusters - 1 else len(sorted_symbols)
            clusters[i] = sorted_symbols[start:end]
        
        return clusters
    
    def get_diversification_benefit(self, weights: Dict[str, float]) -> float:
        """
        计算分散化收益
        
        组合波动率 / 加权平均波动率
        """
        # 计算各资产波动率
        volatilities = {}
        
        for symbol, weight in weights.items():
            if symbol in self.returns_data:
                volatilities[symbol] = self.returns_data[symbol].std()
        
        # 加权平均波动率
        avg_vol = sum(volatilities[s] * weights[s] for s in volatilities)
        
        # 计算组合波动率 (简化)
        corr_matrix = self.get_correlation_matrix()
        
        if corr_matrix.empty:
            return 1.0
        
        # 组合波动率
        portfolio_vol = 0
        
        for s1 in weights:
            for s2 in weights:
                if s1 in volatilities and s2 in volatilities:
                    corr = corr_matrix.loc[s1, s2] if s1 in corr_matrix.index and s2 in corr_matrix.columns else 0
                    portfolio_vol += weights[s1] * weights[s2] * volatilities[s1] * volatilities[s2] * corr
        
        portfolio_vol = np.sqrt(portfolio_vol)
        
        # 分散化比率
        if avg_vol > 0:
            return portfolio_vol / avg_vol
        else:
            return 1.0
    
    def generate_report(self) -> Dict:
        """生成相关性分析报告"""
        corr_matrix = self.get_correlation_matrix()
        
        return {
            'assets': list(self.returns_data.keys()),
            'correlation_matrix': corr_matrix.to_dict(),
            'low_correlation_pairs': [
                {'asset1': p.asset1, 'asset2': p.asset2, 'correlation': round(p.correlation, 3)}
                for p in self.find_low_correlation_pairs(0.3)
            ],
            'high_correlation_pairs': [
                {'asset1': p.asset1, 'asset2': p.asset2, 'correlation': round(p.correlation, 3)}
                for p in self.find_high_correlation_pairs(0.7)
            ],
            'clusters': self.cluster_assets()
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("相关性分析器")
    print("=" * 50)
    
    # 创建分析器
    analyzer = CorrelationAnalyzer()
    
    # 添加模拟数据
    np.random.seed(42)
    
    # BTC 价格 (高波动)
    btc_returns = np.random.normal(0.001, 0.03, 100)
    btc_prices = 45000 * np.cumprod(1 + btc_returns)
    analyzer.add_price_series("BTC", btc_prices.tolist())
    
    # ETH 价格 (与BTC相关)
    eth_returns = btc_returns * 0.8 + np.random.normal(0, 0.02, 100)
    eth_prices = 2500 * np.cumprod(1 + eth_returns)
    analyzer.add_price_series("ETH", eth_prices.tolist())
    
    # SPY (与BTC负/低相关)
    spy_returns = np.random.normal(0.0005, 0.01, 100)
    spy_prices = 450 * np.cumprod(1 + spy_returns)
    analyzer.add_price_series("SPY", spy_prices.tolist())
    
    # 分析
    print("\n📊 相关性矩阵:")
    corr = analyzer.get_correlation_matrix()
    print(corr)
    
    print("\n📉 低相关性资产对:")
    for pair in analyzer.find_low_correlation_pairs(0.5):
        print(f"  {pair.asset1} - {pair.asset2}: {pair.correlation:.3f}")
    
    print("\n📈 高相关性资产对:")
    for pair in analyzer.find_high_correlation_pairs(0.5):
        print(f"  {pair.asset1} - {pair.asset2}: {pair.correlation:.3f}")
    
    print("\n🎯 聚类:")
    clusters = analyzer.cluster_assets(2)
    for cid, assets in clusters.items():
        print(f"  Cluster {cid}: {assets}")
    
    print("\n📊 分散化收益:")
    weights = {'BTC': 0.4, 'ETH': 0.3, 'SPY': 0.3}
    benefit = analyzer.get_diversification_benefit(weights)
    print(f"  组合波动率/加权波动率: {benefit:.3f}")
