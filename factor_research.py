#!/usr/bin/env python3
"""
因子研究平台
Alpha因子库、因子分析、因子组合
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List, Callable
from dataclasses import dataclass


@dataclass
class Factor:
    """因子"""
    name: str
    description: str
    category: str  # momentum, value, quality, volatility, volume
    compute: Callable  # 计算函数


class FactorLibrary:
    """
    因子库
    
    包含:
    - 动量因子
    - 价值因子
    - 质量因子
    - 波动率因子
    - 成交量因子
    """
    
    def __init__(self):
        self.factors: Dict[str, Factor] = {}
        self._register_default_factors()
    
    def _register_default_factors(self):
        """注册默认因子"""
        
        # 动量因子
        self.register(Factor(
            name="return_1m",
            description="1个月收益率",
            category="momentum",
            compute=lambda df: df['close'].pct_change(20)
        ))
        
        self.register(Factor(
            name="return_3m",
            description="3个月收益率",
            category="momentum",
            compute=lambda df: df['close'].pct_change(60)
        ))
        
        self.register(Factor(
            name="return_6m",
            description="6个月收益率",
            category="momentum",
            compute=lambda df: df['close'].pct_change(120)
        ))
        
        # 波动率因子
        self.register(Factor(
            name="volatility_20d",
            description="20天波动率",
            category="volatility",
            compute=lambda df: df['close'].pct_change().rolling(20).std()
        ))
        
        self.register(Factor(
            name="volatility_60d",
            description="60天波动率",
            category="volatility",
            compute=lambda df: df['close'].pct_change().rolling(60).std()
        ))
        
        # 成交量因子
        self.register(Factor(
            name="volume_ratio",
            description="成交量/平均成交量",
            category="volume",
            compute=lambda df: df['volume'] / df['volume'].rolling(20).mean()
        ))
        
        # 趋势因子
        self.register(Factor(
            name="ma_cross",
            description="MA50/MA200 金叉死叉",
            category="trend",
            compute=lambda df: (df['close'].rolling(50).mean() / 
                             df['close'].rolling(200).mean() - 1)
        ))
        
        # RSI
        self.register(Factor(
            name="rsi_14",
            description="RSI指标",
            category="momentum",
            compute=lambda df: self._compute_rsi(df['close'], 14)
        ))
        
        # 价格因子
        self.register(Factor(
            name="price_to_ma200",
            description="价格/MA200",
            category="value",
            compute=lambda df: df['close'] / df['close'].rolling(200).mean()
        ))
    
    def _compute_rsi(self, prices, period=14):
        """计算RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def register(self, factor: Factor):
        """注册因子"""
        self.factors[factor.name] = factor
    
    def compute(self, df: pd.DataFrame, factor_names: List[str] = None) -> pd.DataFrame:
        """
        计算因子值
        
        Args:
            df: 价格数据
            factor_names: 要计算的因子列表
        
        Returns:
            包含因子值的DataFrame
        """
        if factor_names is None:
            factor_names = list(self.factors.keys())
        
        result = df.copy()
        
        for name in factor_names:
            if name in self.factors:
                try:
                    result[name] = self.factors[name].compute(df)
                except Exception as e:
                    print(f"计算因子 {name} 失败: {e}")
                    result[name] = np.nan
        
        return result
    
    def get_factors_by_category(self, category: str) -> List[Factor]:
        """获取某类别的因子"""
        return [f for f in self.factors.values() if f.category == category]
    
    def list_factors(self) -> Dict[str, List[str]]:
        """列出所有因子"""
        categories = {}
        
        for f in self.factors.values():
            if f.category not in categories:
                categories[f.category] = []
            categories[f.category].append(f.name)
        
        return categories


class FactorAnalyzer:
    """
    因子分析器
    
    分析:
    - IC (Information Coefficient)
    - IR (Information Ratio)
    - 分组回测
    """
    
    def __init__(self, library: FactorLibrary = None):
        self.library = library or FactorLibrary()
    
    def calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算IC (因子与收益的相关系数)"""
        # 去除NaN
        valid = factor_values.notna() & returns.notna()
        
        if valid.sum() < 10:
            return 0
        
        ic = factor_values[valid].corr(returns[valid])
        
        return ic if not pd.isna(ic) else 0
    
    def calculate_ic_series(self, factor: pd.Series, returns: pd.Series, window: int = 20) -> pd.Series:
        """计算滚动IC"""
        ic_series = pd.Series(index=factor.index, dtype=float)
        
        for i in range(window, len(factor)):
            window_factor = factor.iloc[i-window:i]
            window_returns = returns.iloc[i-window:i]
            
            valid = window_factor.notna() & window_returns.notna()
            
            if valid.sum() >= 5:
                ic = window_factor[valid].corr(window_returns[valid])
                ic_series.iloc[i] = ic if not pd.isna(ic) else 0
        
        return ic_series
    
    def analyze_factor(self, df: pd.DataFrame, factor_name: str) -> Dict:
        """分析单个因子"""
        # 计算因子
        factor_values = self.library.compute(df, [factor_name])[factor_name]
        
        # 计算收益
        returns = df['close'].pct_change().shift(-1)
        
        # IC
        ic = self.calculate_ic(factor_values, returns)
        
        # 滚动IC
        ic_series = self.calculate_ic_series(factor_values, returns)
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        # IR
        ir = ic_mean / ic_std if ic_std > 0 else 0
        
        # 分组表现
        factor_quantiles = pd.qcut(factor_values, 5, labels=False, duplicates='drop')
        
        group_returns = {}
        for q in range(5):
            mask = factor_quantiles == q
            if mask.sum() > 0:
                group_returns[f"Q{q+1}"] = returns[mask].mean() * 252
        
        return {
            'factor': factor_name,
            'ic': round(ic, 4),
            'ic_mean': round(ic_mean, 4),
            'ic_std': round(ic_std, 4),
            'ir': round(ir, 4),
            'group_returns': {k: round(v, 4) for k, v in group_returns.items()},
            'spread': round(group_returns.get('Q5', 0) - group_returns.get('Q1', 0), 4)
        }
    
    def analyze_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """分析所有因子"""
        results = []
        
        for factor_name in self.library.list_factors():
            try:
                result = self.analyze_factor(df, factor_name)
                results.append(result)
            except Exception as e:
                print(f"分析 {factor_name} 失败: {e}")
        
        return pd.DataFrame(results).sort_values('ir', ascending=False)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("因子研究平台")
    print("=" * 50)
    
    # 创建因子库
    library = FactorLibrary()
    
    print("\n📊 因子库:")
    for category, factors in library.list_factors().items():
        print(f"  {category}: {factors}")
    
    # 生成测试数据
    np.random.seed(42)
    n = 300
    prices = 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    
    df = pd.DataFrame({
        'close': prices,
        'volume': np.random.uniform(1000, 10000, n)
    })
    
    # 分析器
    analyzer = FactorAnalyzer(library)
    
    print("\n📈 因子分析结果:")
    results = analyzer.analyze_all(df)
    
    print(results[['factor', 'ic', 'ir', 'spread']].head(10).to_string(index=False))
