"""
参数优化器 - Parameter Optimizer
==================================

功能:
- 网格搜索
- 遗传算法优化
- 随机搜索
- Walk-Forward验证

作者: AI量化系统
"""

import numpy as np
import random
from typing import List, Dict, Callable, Tuple
from dataclasses import dataclass
from copy import deepcopy


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict
    best_fitness: float
    history: List[Dict]


class ParameterOptimizer:
    """
    参数优化器
    """
    
    def __init__(self):
        self.population = []
        self.generation = 0
        self.best_individual = None
        self.best_fitness = float('-inf')
    
    def grid_search(self, 
                   param_grid: Dict[str, List],
                   fitness_func: Callable,
                   maximize: bool = True) -> OptimizationResult:
        """
        网格搜索
        
        Args:
            param_grid: 参数网格 {param: [values]}
            fitness_func: 适应度函数 (params) -> score
            maximize: 是否最大化
        
        Returns:
            OptimizationResult
        """
        # 生成所有参数组合
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        best_params = None
        best_fitness = float('-inf') if maximize else float('inf')
        history = []
        
        # 遍历所有组合
        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))
            
            fitness = fitness_func(params)
            history.append({
                'params': params,
                'fitness': fitness
            })
            
            if maximize:
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_params = params
            else:
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_params = params
        
        return OptimizationResult(
            best_params=best_params,
            best_fitness=best_fitness,
            history=history
        )
    
    def random_search(self,
                     param_dist: Dict[str, Tuple],
                     n_iter: int,
                     fitness_func: Callable,
                     maximize: bool = True) -> OptimizationResult:
        """
        随机搜索
        
        Args:
            param_dist: 参数分布 {param: (min, max)}
            n_iter: 迭代次数
            fitness_func: 适应度函数
            maximize: 是否最大化
        """
        best_params = None
        best_fitness = float('-inf') if maximize else float('inf')
        history = []
        
        for _ in range(n_iter):
            # 随机生成参数
            params = {}
            for param, (min_val, max_val) in param_dist.items():
                if isinstance(min_val, int):
                    params[param] = random.randint(min_val, max_val)
                else:
                    params[param] = random.uniform(min_val, max_val)
            
            fitness = fitness_func(params)
            history.append({
                'params': params,
                'fitness': fitness
            })
            
            if maximize:
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_params = params
            else:
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_params = params
        
        return OptimizationResult(
            best_params=best_params,
            best_fitness=best_fitness,
            history=history
        )
    
    def genetic_algorithm(self,
                         param_ranges: Dict[str, List],
                         fitness_func: Callable,
                         population_size: int = 50,
                         generations: int = 50,
                         crossover_rate: float = 0.7,
                         mutation_rate: float = 0.1,
                         maximize: bool = True,
                         elite_ratio: float = 0.1) -> OptimizationResult:
        """
        遗传算法优化
        
        Args:
            param_ranges: 参数范围 {param: [values]}
            fitness_func: 适应度函数
            population_size: 种群大小
            generations: 迭代次数
            crossover_rate: 交叉率
            mutation_rate: 变异率
            maximize: 是否最大化
            elite_ratio: 精英比例
        """
        self.generation = 0
        self.best_fitness = float('-inf') if maximize else float('inf')
        
        # 初始化种群
        keys = list(param_ranges.keys())
        values = list(param_ranges.values())
        
        # 创建个体
        def create_individual():
            return {k: random.choice(v) for k, v in param_ranges.items()}
        
        # 初始化
        population = [create_individual() for _ in range(population_size)]
        
        history = []
        
        for gen in range(generations):
            # 评估适应度
            fitness_scores = []
            for ind in population:
                fitness = fitness_func(ind)
                fitness_scores.append(fitness)
                
                # 记录最佳
                if maximize:
                    if fitness > self.best_fitness:
                        self.best_fitness = fitness
                        self.best_individual = deepcopy(ind)
                else:
                    if fitness < self.best_fitness:
                        self.best_fitness = fitness
                        self.best_individual = deepcopy(ind)
            
            history.append({
                'generation': gen,
                'best_fitness': self.best_fitness,
                'avg_fitness': np.mean(fitness_scores)
            })
            
            # 排序
            if maximize:
                sorted_pop = [x for _, x in sorted(zip(fitness_scores, population), 
                                                  key=lambda x: x[0], reverse=True)]
            else:
                sorted_pop = [x for _, x in sorted(zip(fitness_scores, population), 
                                                  key=lambda x: x[0])]
            
            # 精英保留
            elite_count = int(population_size * elite_ratio)
            elite = sorted_pop[:elite_count]
            
            # 选择
            selected = self._select(population, fitness_scores, 
                                   maximize, population_size - elite_count)
            
            # 交叉
            crossed = self._crossover(selected, crossover_rate)
            
            # 变异
            mutated = self._mutate(crossed, param_ranges, mutation_rate)
            
            # 新一代
            population = elite + mutated
            
            self.generation = gen + 1
            
            if gen % 10 == 0:
                print(f"Generation {gen}: Best fitness = {self.best_fitness:.4f}")
        
        return OptimizationResult(
            best_params=self.best_individual,
            best_fitness=self.best_fitness,
            history=history
        )
    
    def _select(self, population: List[Dict], fitness_scores: List[float],
                maximize: bool, n: int) -> List[Dict]:
        """轮盘赌选择"""
        if not fitness_scores:
            return []
        
        # 适应度归一化
        if maximize:
            min_f = min(fitness_scores)
            max_f = max(fitness_scores)
            if max_f - min_f > 0:
                probs = [(f - min_f) / (max_f - min_f) for f in fitness_scores]
            else:
                probs = [1/len(fitness_scores)] * len(fitness_scores)
        else:
            max_f = max(fitness_scores)
            min_f = min(fitness_scores)
            if max_f - min_f > 0:
                probs = [(max_f - f) / (max_f - min_f) for f in fitness_scores]
            else:
                probs = [1/len(fitness_scores)] * len(fitness_scores)
        
        # 轮盘赌
        selected = []
        for _ in range(n):
            r = random.random()
            cumsum = 0
            for i, p in enumerate(probs):
                cumsum += p
                if cumsum >= r:
                    selected.append(deepcopy(population[i]))
                    break
            else:
                selected.append(deepcopy(population[-1]))
        
        return selected
    
    def _crossover(self, population: List[Dict], rate: float) -> List[Dict]:
        """单点交叉"""
        if len(population) < 2:
            return population
        
        result = []
        
        for i in range(0, len(population), 2):
            if i + 1 >= len(population):
                result.append(deepcopy(population[i]))
                continue
            
            p1 = population[i]
            p2 = population[i + 1]
            
            if random.random() < rate:
                # 随机选择一个父本
                child = deepcopy(p1) if random.random() < 0.5 else deepcopy(p2)
                result.append(child)
            else:
                result.append(deepcopy(p1))
                result.append(deepcopy(p2))
        
        return result
    
    def _mutate(self, population: List[Dict], 
               param_ranges: Dict[str, List], rate: float) -> List[Dict]:
        """变异"""
        for ind in population:
            for param, values in param_ranges.items():
                if random.random() < rate:
                    ind[param] = random.choice(values)
        
        return population


def walk_forward_validate(data: List[Dict],
                        signal_func: Callable,
                        train_window: int = 252,
                        test_window: int = 63,
                        param_ranges: Dict[str, List] = None,
                        fitness_func: Callable = None) -> Dict:
    """
    Walk-Forward 验证
    
    Args:
        data: 数据
        signal_func: 信号函数
        train_window: 训练集大小 (天)
        test_window: 测试集大小 (天)
        param_ranges: 参数范围
        fitness_func: 适应度函数
    
    Returns:
        各周期的结果
    """
    if fitness_func is None:
        # 默认适应度
        def fitness_func(params):
            return random.random()  # 简化
    
    results = []
    
    optimizer = ParameterOptimizer()
    
    i = train_window
    while i + test_window <= len(data):
        # 分割数据
        train_data = data[i - train_window:i]
        test_data = data[i:i + test_window]
        
        # 在训练集上优化
        def train_fitness(params):
            # 简化的训练适应度
            return random.random()
        
        opt_result = optimizer.genetic_algorithm(
            param_ranges, 
            train_fitness,
            population_size=20,
            generations=10
        )
        
        # 在测试集上评估
        capital = 100000
        position = 0
        
        for day in test_data:
            signal = signal_func(train_data + [day], opt_result.best_params)
            price = day['close']
            
            if signal == "BUY" and position == 0:
                position = int(capital * 0.95 / price)
                capital -= position * price
            elif signal == "SELL" and position > 0:
                capital += position * price
                position = 0
        
        if position > 0:
            capital += position * test_data[-1]['close']
        
        test_return = (capital - 100000) / 100000
        
        results.append({
            'train_start': train_data[0]['date'],
            'train_end': train_data[-1]['date'],
            'test_start': test_data[0]['date'],
            'test_end': test_data[-1]['date'],
            'best_params': opt_result.best_params,
            'train_fitness': opt_result.best_fitness,
            'test_return': test_return
        })
        
        # 滑动窗口
        i += test_window
    
    # 汇总
    test_returns = [r['test_return'] for r in results]
    
    return {
        'periods': results,
        'avg_test_return': np.mean(test_returns),
        'win_rate': sum(1 for r in test_returns if r > 0) / len(test_returns) if test_returns else 0
    }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例: 优化均线参数
    import random
    
    # 模拟数据
    data = []
    price = 100
    for i in range(500):
        price *= 1 + random.uniform(-0.02, 0.025)
        data.append({
            'date': f'2024-{i//30+1:02d}-{i%30+1:02d}',
            'close': price,
            'high': price * 1.01,
            'low': price * 0.99
        })
    
    # 策略
    def simple_strategy(data, params):
        fast = params.get('fast', 10)
        slow = params.get('slow', 50)
        
        if len(data) < slow:
            return 'HOLD'
        
        closes = [d['close'] for d in data]
        ma_fast = sum(closes[-fast:]) / fast
        ma_slow = sum(closes[-slow:]) / slow
        
        if ma_fast > ma_slow:
            return 'BUY'
        elif ma_fast < ma_slow:
            return 'SELL'
        return 'HOLD'
    
    # 适应度函数
    def fitness(params):
        cash = 100000
        position = 0
        
        for i in range(50, len(data)):
            signal = simple_strategy(data[:i+1], params)
            price = data[i]['close']
            
            if signal == "BUY" and position == 0:
                position = int(cash * 0.95 / price)
                cash -= position * price
            elif signal == "SELL" and position > 0:
                cash += position * price
                position = 0
        
        if position > 0:
            cash += position * data[-1]['close']
        
        return (cash - 100000) / 100000
    
    # 参数范围
    param_ranges = {
        'fast': [5, 8, 10, 12, 15],
        'slow': [20, 30, 50, 60, 80]
    }
    
    # 优化
    optimizer = ParameterOptimizer()
    result = optimizer.genetic_algorithm(
        param_ranges,
        fitness,
        population_size=30,
        generations=20
    )
    
    print(f"Best params: {result.best_params}")
    print(f"Best fitness: {result.best_fitness:.2%}")
