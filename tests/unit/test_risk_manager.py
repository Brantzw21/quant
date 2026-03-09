"""
风控模块单元测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_manager import RiskManager, PositionSizingMethod


class TestRiskManager:
    """RiskManager类测试"""
    
    def test_risk_manager_init(self):
        """测试风控管理器初始化"""
        rm = RiskManager()
        assert rm.stop_loss_pct == 0.05
        assert rm.take_profit_pct == 0.15
        assert rm.max_position_pct == 0.95
    
    def test_risk_manager_custom_config(self):
        """测试自定义配置"""
        config = {
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.10,
            'max_position_pct': 0.8
        }
        rm = RiskManager(config)
        assert rm.stop_loss_pct == 0.03
        assert rm.take_profit_pct == 0.10
        assert rm.max_position_pct == 0.8
    
    def test_calculate_position_size_fixed(self):
        """测试固定仓位计算"""
        rm = RiskManager()
        size = rm.calculate_position_size(
            capital=10000,
            price=50000,
            method=PositionSizingMethod.FIXED,
            params={'pct': 0.5}
        )
        # 10000 * 0.5 / 50000 = 0.1
        assert size == 0
    
    def test_calculate_position_size_kelly(self):
        """测试Kelly仓位计算"""
        rm = RiskManager()
        size = rm.calculate_position_size(
            capital=10000,
            price=100,
            method=PositionSizingMethod.KELLY,
            params={'win_rate': 0.6, 'avg_win': 1.2, 'avg_loss': 1.0}
        )
        # Kelly = (0.6 * 1.2 - 0.4) / 1.2 = 0.267, 半仓 = 0.133
        # position = 10000 * 0.133 / 100 = 13.3 → 13
        assert size == 13
    
    def test_calculate_position_size_kelly_zero_loss(self):
        """测试Kelly仓位计算-零亏损"""
        rm = RiskManager()
        size = rm.calculate_position_size(
            capital=10000,
            price=100,
            method=PositionSizingMethod.KELLY,
            params={'win_rate': 0.5, 'avg_win': 1.0, 'avg_loss': 0}
        )
        # avg_loss为0时返回0
        assert size == 0
    
    def test_check_stop_loss_hit(self):
        """测试止损触发"""
        rm = RiskManager({'stop_loss_pct': 0.05})
        # 买入价100, 当前价94, 跌幅6% > 5%止损
        result = rm.check_stop_loss(entry_price=100, current_price=94)
        assert result == True
    
    def test_check_stop_loss_not_hit(self):
        """测试止损未触发"""
        rm = RiskManager({'stop_loss_pct': 0.05})
        # 买入价100, 当前价97, 跌幅3% < 5%止损
        result = rm.check_stop_loss(entry_price=100, current_price=97)
        assert result == False
    
    def test_check_take_profit_hit(self):
        """测试止盈触发"""
        rm = RiskManager({'take_profit_pct': 0.15})
        # 买入价100, 当前价116, 涨幅16% > 15%止盈
        result = rm.check_take_profit(entry_price=100, current_price=116)
        assert result == True
    
    def test_check_take_profit_not_hit(self):
        """测试止盈未触发"""
        rm = RiskManager({'take_profit_pct': 0.15})
        # 买入价100, 当前价110, 涨幅10% < 15%止盈
        result = rm.check_take_profit(entry_price=100, current_price=110)
        assert result == False


class TestPositionSizingMethod:
    """仓位计算方法枚举测试"""
    
    def test_position_sizing_method_values(self):
        """测试枚举值"""
        assert PositionSizingMethod.FIXED.value == "fixed"
        assert PositionSizingMethod.KELLY.value == "kelly"
        assert PositionSizingMethod.VOLATILITY.value == "volatility"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
