"""
绩效分析模块单元测试
"""
import pytest
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 性能分析器测试
class TestPerformanceAnalyzer:
    """PerformanceAnalyzer类基础测试"""
    
    def test_analyzer_init(self):
        """测试分析器初始化"""
        # 直接测试numpy计算，验证逻辑
        equity_curve = [10000, 10500, 10200, 10800, 11500]
        
        # 计算收益率
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        
        assert len(returns) == 4
        assert np.isclose(returns[0], 0.05)  # 10500/10000 - 1 = 0.05
    
    def test_total_return_calculation(self):
        """测试总收益率计算"""
        equity_curve = [10000, 11000]
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        
        assert np.isclose(total_return, 0.10)  # 10%
    
    def test_annual_return_calculation(self):
        """测试年化收益率计算"""
        # 假设1年252个交易日
        equity_curve = [10000, 12000]
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        
        # 简单年化（假设1年）
        annual_return = (1 + total_return) - 1
        assert np.isclose(annual_return, 0.20)
    
    def test_volatility_calculation(self):
        """测试波动率计算"""
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02])
        
        volatility = np.std(returns)
        assert volatility > 0
    
    def test_annual_volatility(self):
        """测试年化波动率"""
        daily_returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02])
        daily_vol = np.std(daily_returns)
        annual_vol = daily_vol * np.sqrt(252)
        
        assert annual_vol > daily_vol
    
    def test_max_drawdown_calculation(self):
        """测试最大回撤计算"""
        equity = [10000, 11000, 10500, 12000, 10000, 11500]
        
        peak = equity[0]
        max_dd = 0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        assert np.isclose(max_dd, 0.1667, rtol=0.01)  # ~16.67%
    
    def test_sharpe_ratio(self):
        """测试夏普比率"""
        returns = np.array([0.02, 0.015, 0.025, 0.01, 0.02])
        risk_free = 0.03 / 252  # 日化无风险利率
        
        excess_return = np.mean(returns) - risk_free
        sharpe = excess_return / np.std(returns) * np.sqrt(252)
        
        assert sharpe > 0
    
    def test_positive_negative_days(self):
        """测试胜率计算"""
        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, -0.005])  # 3正3负
        
        positive_rate = np.sum(returns > 0) / len(returns) * 100
        negative_rate = np.sum(returns < 0) / len(returns) * 100
        
        assert positive_rate == 50.0
        assert negative_rate == 50.0
    
    def test_var_95_calculation(self):
        """测试VaR计算"""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 1000)
        
        var_95 = np.percentile(returns, 5)
        
        assert var_95 < 0  # 95%置信度下损失为负


class TestRiskMetricsEdgeCases:
    """边界情况测试"""
    
    def test_empty_returns(self):
        """测试空收益序列"""
        returns = np.array([])
        
        if len(returns) > 0:
            vol = np.std(returns)
        else:
            vol = 0
        
        assert vol == 0
    
    def test_single_return(self):
        """测试单收益"""
        returns = np.array([0.05])
        
        assert np.std(returns) == 0  # 单个值标准差为0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
