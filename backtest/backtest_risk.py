"""
回测风控模块
从 backtest_engine.py 提取的 RiskManager 类
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class BacktestRiskManager:
    """回测风控管理器 - ATR 动态止盈止损"""
    
    def __init__(self,
                 max_position_pct: float = 0.5,   # 最大持仓比例
                 max_daily_trades: int = 10,       # 日内最大交易次数
                 max_drawdown_pct: float = 0.2,    # 最大回撤比例
                 atr_multiplier: float = 1.5):     # ATR 倍数
        self.max_position_pct = max_position_pct
        self.max_daily_trades = max_daily_trades
        self.max_drawdown_pct = max_drawdown_pct
        self.atr_multiplier = atr_multiplier
        
        self.daily_trade_count = 0
        self.peak_equity = 0
        self.trades_today = []
    
    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ATR (Average True Range)
        
        TR = max(H-L, |H-PC|, |L-PC|)
        ATR = TR 的均值
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算 TR
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr.iloc[-1]
    
    def compute_stop_levels(self, price: float, atr: float, side: str) -> Tuple[float, float]:
        """
        计算止盈止损价位
        
        Args:
            price: 当前价格
            atr: ATR 值
            side: LONG 或 SHORT
        
        Returns:
            (stop_loss, take_profit)
        """
        if side == "LONG":
            # 多头: 止损在价格下方 1.5x ATR，止盈在上方 3x ATR
            stop_loss = price - atr * self.atr_multiplier
            take_profit = price + atr * self.atr_multiplier * 2
        else:  # SHORT
            # 空头: 止损在价格上方 1.5x ATR，止盈在下方 3x ATR
            stop_loss = price + atr * self.atr_multiplier
            take_profit = price - atr * self.atr_multiplier * 2
        
        return stop_loss, take_profit
    
    def check_stop_take(self, price: float, entry: float, side: str, 
                       stop_loss: float, take_profit: float) -> Tuple[bool, Optional[str]]:
        """
        检查是否触发止盈止损
        
        Returns:
            (triggered: bool, exit_type: str)
        """
        if side == "LONG":
            if price <= stop_loss:
                return True, "STOP_LOSS"
            if price >= take_profit:
                return True, "TAKE_PROFIT"
        else:  # SHORT
            if price >= stop_loss:
                return True, "STOP_LOSS"
            if price <= take_profit:
                return True, "TAKE_PROFIT"
        
        return False, None
    
    def check_position_limit(self, current_pct: float, new_pct: float) -> bool:
        """检查持仓限制"""
        return (current_pct + new_pct) <= self.max_position_pct
    
    def check_drawdown(self, current_equity: float, initial_equity: float) -> bool:
        """检查回撤限制"""
        if self.peak_equity == 0:
            self.peak_equity = initial_equity
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        return drawdown >= self.max_drawdown_pct
    
    def check_daily_trades(self) -> bool:
        """检查日内交易次数"""
        return self.daily_trade_count < self.max_daily_trades
    
    def record_trade(self):
        """记录交易次数"""
        self.daily_trade_count += 1
    
    def reset_daily(self):
        """重置日内计数"""
        self.daily_trade_count = 0
        self.trades_today = []
