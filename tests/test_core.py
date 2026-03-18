#!/usr/bin/env python3
"""
单元测试
pytest测试用例
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')


# ====== 测试配置 ======
@pytest.fixture
def sample_data():
    """测试数据"""
    np.random.seed(42)
    n = 100
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    
    return pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.uniform(1000, 10000, n)
    })


# ====== 测试风险管理 ======
class TestRiskManager:
    """测试风控模块"""
    
    def test_position_sizing(self):
        """测试仓位计算"""
        from risk_manager import RiskManager
        
        rm = RiskManager()
        
        # 测试固定仓位
        size = rm.calculate_position_size(
            capital=10000,
            price=50000,
            method="fixed",
            params={'pct': 0.5}
        )
        
        assert size > 0, "仓位计算应该返回正值"
    
    def test_stop_loss(self):
        """测试止损计算"""
        from risk_manager import RiskManager
        
        rm = RiskManager({'stop_loss_pct': 0.05})
        
        # 假设买入价50000，止损价47500
        stop_price = rm.calculate_stop_loss(50000, 'long')
        
        assert stop_price == 47500, "5%止损应该计算正确"


# ====== 测试回测引擎 ======
class TestBacktestEngine:
    """测试回测引擎"""
    
    def test_simple_backtest(self, sample_data):
        """测试简单回测"""
        from enhanced_backtest import EnhancedBacktestEngine, BacktestConfig
        
        config = BacktestConfig(initial_capital=10000)
        engine = EnhancedBacktestEngine(config)
        
        # 简单信号
        signals = pd.Series(0, index=range(len(sample_data)))
        signals.iloc[10] = 1  # 买入
        signals.iloc[30] = -1  # 卖出
        
        # 运行回测
        result = engine.run(sample_data, signals)
        
        assert result is not None, "回测应该返回结果"
        assert 'total_return' in result, "结果应包含总收益"


# ====== 测试信号生成 ======
class TestSignalGenerator:
    """测试信号生成"""
    
    def test_signal_format(self):
        """测试信号格式"""
        from signals import generate_signal
        
        signal = generate_signal("BTCUSDT")
        
        assert signal is not None, "应该返回信号"
        assert 'signal' in signal, "信号应包含signal字段"
        assert 'confidence' in signal, "信号应包含confidence"


# ====== 测试数据管理器 ======
class TestDataManager:
    """测试数据管理"""
    
    def test_baostock_connection(self):
        """测试Baostock连接"""
        try:
            import baostock as bs
            lg = bs.login()
            assert lg.error_code == '0', "Baostock登录应该成功"
            bs.logout()
        except ImportError:
            pytest.skip("baostock未安装")


# ====== 测试性能分析 ======
class TestPerformanceAnalyzer:
    """测试性能分析"""
    
    def test_sharpe_calculation(self):
        """测试夏普比率计算"""
        from performance_analyzer import PerformanceAnalyzer, Trade
        
        # 模拟交易
        trades = [
            Trade("2026-01-01", "BTC", "BUY", 45000, 0.1, pnl_pct=0.02),
            Trade("2026-01-05", "BTC", "SELL", 45900, 0.1, pnl_pct=0.02),
        ]
        
        analyzer = PerformanceAnalyzer(trades)
        
        sharpe = analyzer.sharpe_ratio()
        
        assert sharpe is not None, "应该计算夏普比率"
    
    def test_win_rate(self):
        """测试胜率计算"""
        from performance_analyzer import PerformanceAnalyzer, Trade
        
        trades = [
            Trade("2026-01-01", "BTC", "BUY", 45000, 0.1, pnl_pct=0.02),
            Trade("2026-01-05", "BTC", "SELL", 44000, 0.1, pnl_pct=-0.02),
        ]
        
        analyzer = PerformanceAnalyzer(trades)
        win_rate = analyzer.win_rate()
        
        assert 0 <= win_rate <= 1, "胜率应在0-1之间"


# ====== 测试相关性分析 ======
class TestCorrelationAnalyzer:
    """测试相关性分析"""
    
    def test_correlation_matrix(self):
        """测试相关性矩阵"""
        from correlation_analyzer import CorrelationAnalyzer
        
        analyzer = CorrelationAnalyzer()
        
        # 添加数据
        np.random.seed(42)
        btc = np.cumprod(1 + np.random.normal(0.001, 0.03, 100))
        eth = btc * 0.8 + np.random.normal(0, 0.02, 100)
        
        analyzer.add_price_series("BTC", btc.tolist())
        analyzer.add_price_series("ETH", eth.tolist())
        
        corr = analyzer.calculate_correlation("BTC", "ETH")
        
        assert -1 <= corr <= 1, "相关性应在-1到1之间"


# ====== 测试策略 ======
class TestStrategy:
    """测试策略"""
    
    def test_rsi_strategy(self, sample_data):
        """测试RSI策略"""
        from light_strategy import calculate_indicators
        
        # 计算指标
        data = calculate_indicators(sample_data)
        
        assert 'rsi' in data.columns, "应该计算RSI指标"
        assert data['rsi'].notna().any(), "RSI应该有值"


# ====== 运行测试 ======
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
