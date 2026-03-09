"""
投资组合模块单元测试
"""
import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio import Portfolio


class MockPosition:
    """Mock持仓"""
    def __init__(self, volume=0, value=0):
        self.volume = volume
        self.value = value


class MockAccount:
    """Mock账户"""
    def __init__(self, total_value=0, positions=None):
        self.total_value = total_value
        self.positions = positions or {}
    
    def update(self, data):
        pass


class TestPortfolio:
    """Portfolio类测试"""
    
    def test_portfolio_init(self):
        """测试组合初始化"""
        p = Portfolio("test_portfolio")
        assert p.name == "test_portfolio"
        assert p.total_value == 0
        assert len(p.accounts) == 0
    
    def test_add_account(self):
        """测试添加账户"""
        p = Portfolio()
        account = MockAccount(total_value=10000)
        p.add_account("acc1", account, weight=1.0)
        
        assert "acc1" in p.accounts
        assert p.strategies["acc1"] == 1.0
    
    def test_remove_account(self):
        """测试移除账户"""
        p = Portfolio()
        account = MockAccount(total_value=10000)
        p.add_account("acc1", account)
        p.remove_account("acc1")
        
        assert "acc1" not in p.accounts
    
    def test_update_total_value(self):
        """测试更新总价值"""
        p = Portfolio()
        p.add_account("acc1", MockAccount(total_value=10000))
        p.add_account("acc2", MockAccount(total_value=20000))
        p.update()
        
        assert p.total_value == 30000
    
    def test_get_position_summary(self):
        """测试持仓汇总"""
        p = Portfolio()
        # 创建带有持仓的账户
        acc1 = MockAccount(total_value=10000, positions={
            "BTC": MockPosition(volume=0.5, value=5000),
            "ETH": MockPosition(volume=10, value=5000)
        })
        p.add_account("acc1", acc1)
        p.update()
        
        summary = p.get_position_summary()
        assert len(summary) == 2
        # 验证权重计算
        btc_pos = next(s for s in summary if s['symbol'] == 'BTC')
        assert btc_pos['weight'] == 50.0


class TestPortfolioSorting:
    """组合排序测试"""
    
    def test_position_summary_sorted_by_weight(self):
        """测试持仓按权重排序"""
        p = Portfolio()
        acc1 = MockAccount(total_value=10000, positions={
            "BTC": MockPosition(volume=0.1, value=1000),
            "ETH": MockPosition(volume=50, value=5000),
            "SOL": MockPosition(volume=100, value=4000)
        })
        p.add_account("acc1", acc1)
        p.update()
        
        summary = p.get_position_summary()
        # 验证按权重降序排列
        assert summary[0]['symbol'] == 'ETH'  # 50%
        assert summary[1]['symbol'] == 'SOL'  # 40%
        assert summary[2]['symbol'] == 'BTC'  # 10%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
