#!/usr/bin/env python3
"""
统计检验工具
策略表现显著性检验
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TestResult:
    """检验结果"""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    confidence_level: float = 0.95
    interpretation: str = ""


class StatisticalTester:
    """
    统计检验工具
    
    检验:
    - 正态性检验
    - 平稳性检验
    - 显著性检验
    - 分布检验
    """
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level
    
    def jarque_bera(self, data: np.ndarray) -> TestResult:
        """
        Jarque-Bera 正态性检验
        """
        n = len(data)
        
        if n < 8:
            return TestResult(
                test_name="Jarque-Bera",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="数据量不足"
            )
        
        # 计算统计量
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return TestResult(
                test_name="Jarque-Bera",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="标准差为0"
            )
        
        # 偏度和峰度
        skewness = np.mean(((data - mean) / std) ** 3)
        kurtosis = np.mean(((data - mean) / std) ** 4)
        
        # JB统计量
        jb = (n / 6) * (skewness ** 2 + (kurtosis - 3) ** 2 / 4)
        
        # p值 (卡方分布，df=2)
        from scipy import stats
        p_value = 1 - stats.chi2.cdf(jb, 2)
        
        significant = p_value < self.alpha
        
        return TestResult(
            test_name="Jarque-Bera",
            statistic=jb,
            p_value=p_value,
            significant=significant,
            confidence_level=self.confidence_level,
            interpretation="数据服从正态分布" if not significant else "数据不服从正态分布"
        )
    
    def adf_test(self, data: np.ndarray, max_lag: int = None) -> TestResult:
        """
        Augmented Dickey-Fuller 平稳性检验
        
        H0: 序列存在单位根 (非平稳)
        """
        try:
            from scipy import stats
        except ImportError:
            return TestResult(
                test_name="ADF",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="scipy未安装"
            )
        
        # 简化ADF
        n = len(data)
        
        if n < 20:
            return TestResult(
                test_name="ADF",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="数据量不足"
            )
        
        # 简单回归
        y = data[1:]
        x = data[:-1]
        
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # t统计量
            t_stat = slope / std_err if std_err > 0 else 0
            
            # p值
            from scipy import stats
            p_value = stats.t.sf(np.abs(t_stat), n - 2) * 2
            
            significant = p_value < self.alpha
            
            return TestResult(
                test_name="ADF",
                statistic=t_stat,
                p_value=p_value,
                significant=significant,
                confidence_level=self.confidence_level,
                interpretation="序列平稳" if significant else "序列非平稳 (存在单位根)"
            )
        except:
            return TestResult(
                test_name="ADF",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="计算失败"
            )
    
    def t_test(self, sample1: np.ndarray, sample2: np.ndarray = None, 
               paired: bool = False) -> TestResult:
        """
        T检验
        
        Args:
            sample1: 样本1
            sample2: 样本2 (如果为None，则是单样本t检验)
            paired: 是否配对样本
        """
        try:
            from scipy import stats
        except ImportError:
            return TestResult(
                test_name="T-test",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="scipy未安装"
            )
        
        if sample2 is None:
            # 单样本t检验 (检验均值是否显著不为0)
            t_stat, p_value = stats.ttest_1samp(sample1, 0)
        elif paired:
            # 配对t检验
            if len(sample1) != len(sample2):
                return TestResult(
                    test_name="T-test (paired)",
                    statistic=0,
                    p_value=1,
                    significant=False,
                    confidence_level=self.confidence_level,
                    interpretation="配对样本数量不匹配"
                )
            t_stat, p_value = stats.ttest_rel(sample1, sample2)
        else:
            # 独立样本t检验
            t_stat, p_value = stats.ttest_ind(sample1, sample2)
        
        significant = p_value < self.alpha
        
        return TestResult(
            test_name="T-test",
            statistic=t_stat,
            p_value=p_value,
            significant=significant,
            confidence_level=self.confidence_level,
            interpretation="差异显著" if significant else "差异不显著"
        )
    
    def kolmogorov_smirnov(self, sample: np.ndarray, distribution: str = 'norm') -> TestResult:
        """
        Kolmogorov-Smirnov 分布检验
        """
        try:
            from scipy import stats
        except ImportError:
            return TestResult(
                test_name="KS",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="scipy未安装"
            )
        
        if distribution == 'norm':
            mean = np.mean(sample)
            std = np.std(sample)
            d_stat, p_value = stats.kstest(sample, 'norm', args=(mean, std))
        
        significant = p_value < self.alpha
        
        return TestResult(
            test_name="KS",
            statistic=d_stat,
            p_value=p_value,
            significant=significant,
            confidence_level=self.confidence_level,
            interpretation="服从指定分布" if not significant else "不服从指定分布"
        )
    
    def runs_test(self, data: np.ndarray) -> TestResult:
        """
        运行检验 (检验随机性)
        
        H0: 数据是随机的
        """
        n = len(data)
        
        if n < 20:
            return TestResult(
                test_name="Runs",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="数据量不足"
            )
        
        # 转为0/1 (中位数之上为1)
        median = np.median(data)
        runs = []
        prev = None
        
        for v in data:
            current = 1 if v > median else 0
            if current != prev:
                runs.append(current)
            prev = current
        
        # 计算期望和方差
        n1 = sum(1 for r in runs if r == 1)
        n2 = sum(1 for r in runs if r == 0)
        
        if n1 == 0 or n2 == 0:
            return TestResult(
                test_name="Runs",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="无法计算"
            )
        
        n_runs = len(runs)
        
        # 期望值
        expected = (2 * n1 * n2) / (n1 + n2) + 1
        
        # 方差
        var = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
        
        if var <= 0:
            return TestResult(
                test_name="Runs",
                statistic=0,
                p_value=1,
                significant=False,
                confidence_level=self.confidence_level,
                interpretation="方差为0"
            )
        
        # z统计量
        z = (n_runs - expected) / np.sqrt(var)
        
        # p值 (双尾)
        try:
            from scipy import stats
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        except:
            p_value = 1
        
        significant = p_value < self.alpha
        
        return TestResult(
            test_name="Runs",
            statistic=z,
            p_value=p_value,
            significant=significant,
            confidence_level=self.confidence_level,
            interpretation="数据随机" if not significant else "数据不随机"
        )
    
    def run_all_tests(self, returns: np.ndarray, benchmark_returns: np.ndarray = None) -> Dict:
        """
        运行所有检验
        """
        results = {}
        
        # 正态性检验
        results['jarque_bera'] = self.jarque_bera(returns)
        
        # 平稳性检验
        results['adf'] = self.adf_test(returns)
        
        # 随机性检验
        results['runs'] = self.runs_test(returns)
        
        # 分布检验
        results['ks_norm'] = self.kolmogorov_smirnov(returns, 'norm')
        
        # 如果有基准，进行差异检验
        if benchmark_returns is not None:
            results['t_test'] = self.t_test(returns, benchmark_returns)
        
        return results


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("统计检验工具")
    print("=" * 50)
    
    # 创建检验器
    tester = StatisticalTester(confidence_level=0.95)
    
    # 生成测试数据 (正态分布)
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    
    # 基准
    benchmark = np.random.normal(0.0005, 0.01, 100)
    
    # 运行所有检验
    print("\n📊 检验结果:")
    results = tester.run_all_tests(returns, benchmark)
    
    for name, result in results.items():
        status = "✅" if not result.significant else "❌"
        print(f"\n{status} {result.test_name}:")
        print(f"   统计量: {result.statistic:.4f}")
        print(f"   p值: {result.p_value:.4f}")
        print(f"   结论: {result.interpretation}")
