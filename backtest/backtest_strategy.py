"""
回测策略代理模块
从 backtest_engine.py 提取的 StrategyAgent 类
"""

import pandas as pd
from typing import Dict, Callable, Optional


class BacktestStrategyAgent:
    """策略代理 - 调用信号生成"""
    
    def __init__(self, strategy_func: Callable = None):
        self.strategy_func = strategy_func
        self.last_signal = None
    
    def generate_signal(self, data: pd.DataFrame) -> Dict:
        """生成信号
        
        返回格式支持:
        - BUY/SELL/HOLD (旧格式)
        - LONG/SHORT/HOLD (新格式)
        """
        if self.strategy_func:
            signal = self.strategy_func(data)
            # 兼容转换
            if signal.get('signal') == 'BUY':
                signal['signal'] = 'LONG'
            elif signal.get('signal') == 'SELL':
                signal['signal'] = 'SHORT'
            self.last_signal = signal
            return signal
        
        # 默认返回 HOLD
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'reason': 'no strategy'
        }
    
    def get_last_signal(self) -> Optional[Dict]:
        """获取最后信号"""
        return self.last_signal
