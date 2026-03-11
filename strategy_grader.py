#!/usr/bin/env python3
"""
策略评级系统
多维度评估策略表现
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GradeResult:
    """评级结果"""
    overall_score: float  # 综合评分 0-100
    grade: str  # A/B/C/D/E
    dimensions: Dict[str, float]  # 各维度评分
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 缺点
    recommendation: str  # 建议


class StrategyGrader:
    """
    策略评级系统
    
    评分维度:
    - 收益性 (25%)
    - 风险控制 (25%)
    - 稳定性 (20%)
    - 效率 (15%)
    - 适应性 (15%)
    """
    
    def __init__(self):
        # 权重配置
        self.weights = {
            'return': 0.25,
            'risk': 0.25,
            'stability': 0.20,
            'efficiency': 0.15,
            'adaptability': 0.15
        }
    
    def grade(self, performance_data: Dict) -> GradeResult:
        """
        评级
        
        Args:
            performance_data: 绩效数据 {
                'total_return': 0.15,
                'annualized_return': 0.20,
                'sharpe_ratio': 1.5,
                'max_drawdown': 0.10,
                'win_rate': 0.55,
                'profit_factor': 1.8,
                'trade_count': 100,
                'avg_holding_period': 5,
                'volatility': 0.12,
            }
        """
        dimensions = {}
        
        # 1. 收益性评分 (0-100)
        dimensions['return'] = self._grade_return(performance_data)
        
        # 2. 风险控制评分
        dimensions['risk'] = self._grade_risk(performance_data)
        
        # 3. 稳定性评分
        dimensions['stability'] = self._grade_stability(performance_data)
        
        # 4. 效率评分
        dimensions['efficiency'] = self._grade_efficiency(performance_data)
        
        # 5. 适应性评分
        dimensions['adaptability'] = self._grade_adaptability(performance_data)
        
        # 计算综合评分
        overall_score = sum(
            dimensions[k] * self.weights[k] 
            for k in self.weights
        )
        
        # 评级
        grade = self._get_grade(overall_score)
        
        # 优缺点
        strengths, weaknesses = self._analyze_strengths_weaknesses(dimensions, performance_data)
        
        # 建议
        recommendation = self._get_recommendation(grade, dimensions)
        
        return GradeResult(
            overall_score=round(overall_score, 1),
            grade=grade,
            dimensions={k: round(v, 1) for k, v in dimensions.items()},
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation
        )
    
    def _grade_return(self, data: Dict) -> float:
        """收益性评分"""
        total_return = data.get('total_return', 0)
        ann_return = data.get('annualized_return', 0)
        
        # 年化收益评分
        if ann_return > 0.5:
            return 100
        elif ann_return > 0.3:
            return 85
        elif ann_return > 0.2:
            return 70
        elif ann_return > 0.1:
            return 55
        elif ann_return > 0:
            return 40
        else:
            return 20
    
    def _grade_risk(self, data: Dict) -> float:
        """风险控制评分"""
        mdd = data.get('max_drawdown', 1)
        sharpe = data.get('sharpe_ratio', 0)
        
        # 最大回撤评分 (回撤越小越好)
        if mdd < 0.05:
            mdd_score = 100
        elif mdd < 0.10:
            mdd_score = 80
        elif mdd < 0.15:
            mdd_score = 60
        elif mdd < 0.20:
            mdd_score = 40
        else:
            mdd_score = 20
        
        # 夏普比率评分
        if sharpe > 2:
            sharpe_score = 100
        elif sharpe > 1.5:
            sharpe_score = 85
        elif sharpe > 1.0:
            sharpe_score = 70
        elif sharpe > 0.5:
            sharpe_score = 50
        else:
            sharpe_score = 30
        
        return (mdd_score + sharpe_score) / 2
    
    def _grade_stability(self, data: Dict) -> float:
        """稳定性评分"""
        win_rate = data.get('win_rate', 0)
        profit_factor = data.get('profit_factor', 0)
        volatility = data.get('volatility', 1)
        
        # 胜率评分
        if win_rate > 0.6:
            win_score = 100
        elif win_rate > 0.5:
            win_score = 75
        elif win_rate > 0.4:
            win_score = 50
        else:
            win_score = 25
        
        # 盈利因子评分
        if profit_factor > 2:
            pf_score = 100
        elif profit_factor > 1.5:
            pf_score = 75
        elif profit_factor > 1.2:
            pf_score = 50
        else:
            pf_score = 25
        
        # 波动率评分 (波动越小越好)
        if volatility < 0.1:
            vol_score = 100
        elif volatility < 0.15:
            vol_score = 80
        elif volatility < 0.2:
            vol_score = 60
        else:
            vol_score = 40
        
        return (win_score * 0.4 + pf_score * 0.4 + vol_score * 0.2)
    
    def _grade_efficiency(self, data: Dict) -> float:
        """效率评分"""
        trade_count = data.get('trade_count', 0)
        avg_holding = data.get('avg_holding_period', 0)
        
        # 交易次数 (太频繁不一定好)
        if 50 < trade_count < 200:
            count_score = 100
        elif 20 < trade_count < 500:
            count_score = 80
        else:
            count_score = 50
        
        # 平均持仓时间 (适中最好)
        if 1 < avg_holding < 20:
            holding_score = 100
        elif avg_holding <= 1:
            holding_score = 60  # 过于频繁
        else:
            holding_score = 70  # 持仓过长
        
        return (count_score + holding_score) / 2
    
    def _grade_adaptability(self, data: Dict) -> float:
        """适应性评分 - 基于多个指标综合判断"""
        # 这里可以加入更多适应性指标
        # 简化版基于总体表现
        
        score = 70  # 默认
        
        if data.get('sharpe_ratio', 0) > 1:
            score += 10
        if data.get('max_drawdown', 1) < 0.15:
            score += 10
        if data.get('win_rate', 0) > 0.5:
            score += 10
        
        return min(score, 100)
    
    def _get_grade(self, score: float) -> str:
        """根据分数获取评级"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'E'
    
    def _analyze_strengths_weaknesses(self, dimensions: Dict, data: Dict) -> tuple:
        """分析优缺点"""
        strengths = []
        weaknesses = []
        
        # 收益性
        if dimensions['return'] >= 70:
            strengths.append('收益表现优秀')
        elif dimensions['return'] < 40:
            weaknesses.append('收益能力不足')
        
        # 风险
        if dimensions['risk'] >= 70:
            strengths.append('风控能力良好')
        elif dimensions['risk'] < 40:
            weaknesses.append('风险控制需要改进')
        
        # 稳定性
        if dimensions['stability'] >= 70:
            strengths.append('策略稳定性好')
        
        # 夏普
        if data.get('sharpe_ratio', 0) > 1.5:
            strengths.append('风险调整收益优秀')
        
        # 回撤
        if data.get('max_drawdown', 1) < 0.1:
            strengths.append('回撤控制良好')
        
        return strengths, weaknesses
    
    def _get_recommendation(self, grade: str, dimensions: Dict) -> str:
        """获取建议"""
        if grade.startswith('A'):
            return "策略表现优秀，可考虑加大投入"
        elif grade == 'B':
            return "策略表现良好，可继续使用"
        elif grade == 'C':
            return "策略表现一般，建议优化参数"
        elif grade == 'D':
            return "策略表现较差，需要重大改进"
        else:
            return "不建议使用该策略"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("策略评级系统")
    print("=" * 50)
    
    # 创建评级器
    grader = StrategyGrader()
    
    # 测试数据
    performance = {
        'total_return': 0.25,
        'annualized_return': 0.35,
        'sharpe_ratio': 1.8,
        'max_drawdown': 0.08,
        'win_rate': 0.58,
        'profit_factor': 2.0,
        'trade_count': 120,
        'avg_holding_period': 5,
        'volatility': 0.12,
    }
    
    # 评级
    result = grader.grade(performance)
    
    print(f"\n📊 评级结果")
    print(f"  综合评分: {result.overall_score}/100")
    print(f"  评级: {result.grade}")
    
    print(f"\n📈 维度评分:")
    for dim, score in result.dimensions.items():
        print(f"  {dim}: {score}")
    
    print(f"\n✅ 优点:")
    for s in result.strengths:
        print(f"  - {s}")
    
    print(f"\n⚠️ 缺点:")
    for w in result.weaknesses:
        print(f"  - {w}")
    
    print(f"\n💡 建议: {result.recommendation}")
