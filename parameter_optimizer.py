#!/usr/bin/env python3
"""
参数优化器
支持网格搜索、随机搜索、贝叶斯优化
"""

import sys
import os
import json
import time
import random
import numpy as np
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_engine import BacktestEngine


@dataclass
class OptimizationResult:
    """优化结果"""
    params: Dict
    sharpe: float
    total_return: float
    max_drawdown: float
    win_rate: float
    trades: int


class ParameterOptimizer:
    """
    参数优化器
    
    支持方法:
    - Grid Search: 网格搜索
    - Random Search: 随机搜索
    - Bayesian: 贝叶斯优化 (需要 bayesian-optimization 库)
    """
    
    def __init__(self, symbol: str = "BTCUSDT", metric: str = "sharpe"):
        self.symbol = symbol
        self.metric = metric  # sharpe, return, drawdown
        self.results: List[OptimizationResult] = []
        
        # 默认参数范围
        self.param_ranges = {
            'rsi_period': (5, 30),
            'rsi_overbought': (60, 85),
            'rsi_oversold': (15, 40),
            'ma_short': (5, 30),
            'ma_long': (20, 100),
            'stop_loss': (0.01, 0.10),
            'take_profit': (0.03, 0.20),
        }
    
    def grid_search(self, param_grid: Dict = None, max_combinations: int = 100) -> List[OptimizationResult]:
        """
        网格搜索
        
        Args:
            param_grid: 参数网格 {'param': [values]}
            max_combinations: 最大组合数
        
        Returns:
            优化结果列表
        """
        param_grid = param_grid or self._default_grid()
        
        # 生成所有组合
        combinations = self._generate_combinations(param_grid)
        
        if len(combinations) > max_combinations:
            print(f"⚠️ 组合数 {len(combinations)} > {max_combinations}，随机采样")
            combinations = random.sample(combinations, max_combinations)
        
        print(f"🔍 开始网格搜索: {len(combinations)} 个组合")
        
        results = []
        for i, params in enumerate(combinations):
            result = self._evaluate_params(params)
            results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{len(combinations)}")
        
        # 排序
        results.sort(key=lambda x: getattr(x, self.metric), reverse=True)
        
        self.results = results
        return results
    
    def random_search(self, n_iter: int = 50) -> List[OptimizationResult]:
        """
        随机搜索
        
        Args:
            n_iter: 迭代次数
        
        Returns:
            优化结果列表
        """
        print(f"🔍 开始随机搜索: {n_iter} 次")
        
        results = []
        for i in range(n_iter):
            params = self._random_params()
            result = self._evaluate_params(params)
            results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{n_iter}")
        
        # 排序
        results.sort(key=lambda x: getattr(x, self.metric), reverse=True)
        
        self.results = results
        return results
    
    def bayesian_search(self, n_iter: int = 30) -> List[OptimizationResult]:
        """
        贝叶斯优化
        
        Args:
            n_iter: 迭代次数
        
        Returns:
            优化结果列表
        """
        try:
            from bayes_opt import BayesianOptimization
        except ImportError:
            print("❌ bayesian-optimization 未安装，使用随机搜索")
            return self.random_search(n_iter)
        
        print(f"🔍 开始贝叶斯优化: {n_iter} 次")
        
        # 定义目标函数
        def objective(**params):
            result = self._evaluate_params(params)
            return getattr(result, self.metric)
        
        # 参数边界
        pbounds = {}
        for param, (min_val, max_val) in self.param_ranges.items():
            pbounds[param] = (min_val, max_val)
        
        optimizer = BayesianOptimization(
            f=objective,
            pbounds=pbounds,
            random_state=42,
            verbose=2
        )
        
        optimizer.maximize(n_iter=n_iter)
        
        # 转换为结果列表
        results = []
        for i, res in enumerate(optimizer.res):
            results.append(OptimizationResult(
                params=res['params'],
                sharpe=res['target'] if self.metric == 'sharpe' else 0,
                total_return=res['target'] if self.metric == 'total_return' else 0,
                max_drawdown=0,
                win_rate=0,
                trades=0
            ))
        
        self.results = results
        return results
    
    def _default_grid(self) -> Dict:
        """默认参数网格"""
        return {
            'rsi_period': [5, 10, 15, 20, 25],
            'rsi_overbought': [65, 70, 75, 80, 85],
            'rsi_oversold': [15, 20, 25, 30, 35],
            'ma_short': [10, 20, 30],
            'ma_long': [50, 60, 80],
        }
    
    def _generate_combinations(self, param_grid: Dict) -> List[Dict]:
        """生成参数组合"""
        import itertools
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            combinations.append(params)
        
        return combinations
    
    def _random_params(self) -> Dict:
        """随机参数"""
        params = {}
        for param, (min_val, max_val) in self.param_ranges.items():
            if isinstance(min_val, int):
                params[param] = random.randint(min_val, max_val)
            else:
                params[param] = random.uniform(min_val, max_val)
        return params
    
    def _evaluate_params(self, params: Dict) -> OptimizationResult:
        """评估参数"""
        try:
            # 简化版：使用历史数据回测
            # 实际应该调用 BacktestEngine
            
            # 模拟回测结果
            sharpe = random.uniform(-0.5, 2.0)
            total_return = random.uniform(-0.3, 0.5)
            max_drawdown = random.uniform(0.05, 0.3)
            win_rate = random.uniform(0.3, 0.7)
            trades = random.randint(10, 100)
            
            # 根据参数调整 (模拟)
            if 'rsi_period' in params:
                sharpe *= 1 + (params['rsi_period'] - 15) / 100
            
            return OptimizationResult(
                params=params,
                sharpe=round(sharpe, 3),
                total_return=round(total_return, 3),
                max_drawdown=round(max_drawdown, 3),
                win_rate=round(win_rate, 3),
                trades=trades
            )
            
        except Exception as e:
            print(f"评估失败 {params}: {e}")
            return OptimizationResult(
                params=params,
                sharpe=-999,
                total_return=-999,
                max_drawdown=1,
                win_rate=0,
                trades=0
            )
    
    def get_top_params(self, n: int = 5) -> List[Dict]:
        """获取Top N参数"""
        if not self.results:
            return []
        
        top = []
        for r in self.results[:n]:
            top.append({
                'params': r.params,
                'sharpe': r.sharpe,
                'return': r.total_return,
                'drawdown': r.max_drawdown,
                'win_rate': r.win_rate,
                'trades': r.trades
            })
        
        return top
    
    def save_results(self, filepath: str = "/root/.openclaw/workspace/quant/quant/data/optimization_results.json"):
        """保存优化结果"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'metric': self.metric,
            'top_params': self.get_top_params(10)
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("参数优化器")
    print("=" * 50)
    
    # 创建优化器
    optimizer = ParameterOptimizer("BTCUSDT", metric="sharpe")
    
    # 随机搜索
    print("\n🔍 随机搜索...")
    results = optimizer.random_search(n_iter=20)
    
    # 显示结果
    print("\n📊 Top 5 参数:")
    for i, r in enumerate(results[:5], 1):
        print(f"\n{i}. Sharpe: {r.sarpe:.3f}, Return: {r.total_return:.1%}")
        print(f"   参数: {r.params}")
    
    # 保存
    optimizer.save_results()
    print("\n✅ 结果已保存")
