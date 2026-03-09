"""
信号模块单元测试
"""
import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals import Signal, SignalType, Order, OrderType, OrderStatus


class TestSignal:
    """Signal类测试"""
    
    def test_signal_creation(self):
        """测试信号创建"""
        sig = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            price=50000,
            volume=0.1,
            reason="RSI oversold"
        )
        assert sig.symbol == "BTCUSDT"
        assert sig.signal_type == SignalType.BUY
        assert sig.price == 50000
        assert sig.volume == 0.1
        assert sig.confidence == 0.5
    
    def test_signal_to_dict(self):
        """测试信号转字典"""
        sig = Signal(
            symbol="ETHUSDT",
            signal_type=SignalType.SELL,
            price=3000,
            volume=1.0
        )
        d = sig.to_dict()
        assert d["symbol"] == "ETHUSDT"
        assert d["type"] == "SELL"
        assert d["price"] == 3000
        assert "timestamp" in d


    """Order类class TestOrder:
测试"""
    
    def test_order_creation(self):
        """测试订单创建"""
        order = Order(
            symbol="BTCUSDT",
            direction="long",
            order_type=OrderType.MARKET,
            price=50000,
            volume=0.1
        )
        assert order.symbol == "BTCUSDT"
        assert order.direction == "long"
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
    
    def test_order_to_dict(self):
        """测试订单转字典"""
        order = Order(
            symbol="BTCUSDT",
            direction="short",
            order_type=OrderType.LIMIT,
            price=49000,
            volume=0.2
        )
        d = order.to_dict()
        assert d["symbol"] == "BTCUSDT"
        assert d["direction"] == "short"
        assert d["type"] == "LIMIT"
        assert d["status"] == "PENDING"


class TestSignalType:
    """SignalType枚举测试"""
    
    def test_signal_type_values(self):
        """测试信号类型值"""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"


class TestOrderType:
    """OrderType枚举测试"""
    
    def test_order_type_values(self):
        """测试订单类型值"""
        assert OrderType.MARKET.value == "MARKET"
        assert OrderType.LIMIT.value == "LIMIT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
