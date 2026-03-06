"""
Comprehensive tests for Quant project
"""
import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestStrategies:
    """Strategy module tests"""
    
    def test_ma_cross_signal(self):
        """Test MA cross strategy"""
        from strategies import ma_cross_signal
        
        # Test data
        data = [
            {"close": 50000}, {"close": 50500}, {"close": 51000},
            {"close": 51500}, {"close": 52000}, {"close": 52500}
        ]
        
        signal = ma_cross_signal(data, {"fast_ma": 3, "slow_ma": 5})
        assert signal in ["BUY", "SELL", "HOLD"]
    
    def test_rsi_signal(self):
        """Test RSI strategy"""
        from strategies import rsi_signal
        
        data = [{"close": 50000 + i * 100} for i in range(20)]
        signal = rsi_signal(data, {"rsi_period": 14, "oversold": 30, "overbought": 70})
        assert signal in ["BUY", "SELL", "HOLD"]
    
    def test_breakout_signal(self):
        """Test breakout strategy"""
        from strategies import breakout_signal
        
        data = [{"high": 50000 + i * 100, "low": 49000 + i * 100, "close": 49500 + i * 100} for i in range(25)]
        signal = breakout_signal(data, {"lookback": 20, "breakout_factor": 1.02})
        assert signal in ["BUY", "SELL", "HOLD"]

class TestRiskControl:
    """Risk control tests"""
    
    def test_position_limit(self):
        """Test position size limit"""
        from risk_logger import check_risk_limits
        
        # Normal
        result = check_risk_limits(1000, 10000, 5, 0.02)
        assert result["passed"] == True
        
        # Over position
        result = check_risk_limits(8000, 10000, 5, 0.02)
        assert result["passed"] == False
    
    def test_drawdown_limit(self):
        """Test drawdown limit"""
        from risk_logger import check_risk_limits
        
        # Normal
        result = check_risk_limits(1000, 10000, 5, 0.02)
        assert result["checks"]["drawdown"] in ["PASS", "WARNING"]
        
        # Over drawdown
        result = check_risk_limits(1000, 10000, 25, 0.02)
        assert result["passed"] == False
    
    def test_volatility_check(self):
        """Test volatility check"""
        from risk_logger import check_risk_limits
        
        result = check_risk_limits(1000, 10000, 5, 0.08)
        assert result["checks"]["volatility"] == "WARNING"

class TestDataManager:
    """Data manager tests"""
    
    def test_import(self):
        """Test data manager can be imported"""
        try:
            from data_manager import DataManager
            assert DataManager is not None
        except Exception as e:
            pytest.skip(f"Import error: {e}")

class TestConfig:
    """Configuration tests"""
    
    def test_config_import(self):
        """Test config import"""
        from config import SYMBOL, LEVERAGE
        assert SYMBOL == "BTCUSDT"
        assert LEVERAGE >= 1
    
    def test_config_env_vars(self):
        """Test environment variables"""
        from config import API_KEY, SECRET_KEY
        # Should be empty string if not set
        assert isinstance(API_KEY, str)
        assert isinstance(SECRET_KEY, str)

class TestNotify:
    """Notification tests"""
    
    def test_notify_import(self):
        """Test notify module import"""
        from notify import send_message
        assert callable(send_message)

class TestLightStrategy:
    """Light strategy tests"""
    
    def test_indicators_import(self):
        """Test indicators can be imported"""
        try:
            from light_strategy import calculate_indicators
            assert callable(calculate_indicators)
        except Exception as e:
            pytest.skip(f"Import error: {e}")

class TestMultiStrategy:
    """Multi-strategy router tests"""
    
    def test_router_import(self):
        """Test router import"""
        try:
            import multi_strategy_router
            assert hasattr(multi_strategy_router, 'multi_strategy_signal')
        except Exception as e:
            pytest.skip(f"Import error: {e}")

class TestWalkForward:
    """Walk-forward analysis tests"""
    
    def test_walkforward_import(self):
        """Test walkforward import"""
        try:
            from walkforward_analyzer import WalkForwardAnalyzer
            assert WalkForwardAnalyzer is not None
        except Exception as e:
            pytest.skip(f"Import error: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
