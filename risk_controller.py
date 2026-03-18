#!/usr/bin/env python3
"""
统一风控模块
集成仓位管理、止损止盈、账户风控

Features:
- 动态仓位计算
- ATR 止损/止盈
- 账户级风控 (回撤熔断/连亏冷却)
- 多策略风控隔离
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json

import numpy as np
import pandas as pd


class RiskState(Enum):
    """风控状态"""
    NORMAL = "NORMAL"       # 正常
    DEFENSIVE = "DEFENSIVE" # 防御状态
    HALTON = "HALTON"       # 暂停交易
    COOLDOWN = "COOLDOWN"   # 冷却中


@dataclass
class RiskConfig:
    """风控配置"""
    # 仓位
    max_position_pct: float = 0.5      # 最大仓位 50%
    min_position_pct: float = 0.1      # 最小仓位 10%
    
    # 止损止盈
    stop_loss_pct: float = 0.03        # 止损 3%
    take_profit_pct: float = 0.08     # 止盈 8%
    use_atr_stop: bool = True          # 使用 ATR 动态止损
    atr_multiplier: float = 1.5        # ATR 倍数
    
    # 账户风控
    max_drawdown_pct: float = 0.15     # 回撤熔断 15%
    daily_loss_pct: float = 0.05      # 日亏熔断 5%
    max_consecutive_losses: int = 3    # 连亏次数
    cooldown_minutes: int = 60         # 冷却时间
    
    # 交易限制
    max_daily_trades: int = 10        # 每日最大交易次数
    min_trade_interval_seconds: int = 60  # 最小交易间隔


@dataclass
class RiskStateData:
    """风控状态数据 (持久化)"""
    # 账户
    peak_equity: float = 0.0           # 历史最高权益
    current_equity: float = 0.0        # 当前权益
    daily_pnl: float = 0.0             # 今日盈亏
    daily_trades: int = 0               # 今日交易次数
    last_trade_time: Optional[datetime] = None
    
    # 连亏
    consecutive_losses: int = 0         # 连亏次数
    last_trade_result: Optional[str] = None  # LAST_TRADE_RESULT
    
    # 状态
    state: RiskState = RiskState.NORMAL
    halt_reason: str = ""
    cooldown_until: Optional[datetime] = None
    
    # 策略隔离
    strategy_states: Dict[str, dict] = field(default_factory=dict)
    
    def save(self, filepath: str):
        """保存状态"""
        data = {
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'consecutive_losses': self.consecutive_losses,
            'last_trade_result': self.last_trade_result,
            'state': self.state.value,
            'halt_reason': self.halt_reason,
            'cooldown_until': self.cooldown_until.isoformat() if self.cooldown_until else None,
            'strategy_states': self.strategy_states,
        }
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'RiskStateData':
        """加载状态"""
        if not os.path.exists(filepath):
            return cls()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        state = cls()
        state.peak_equity = data.get('peak_equity', 0)
        state.current_equity = data.get('current_equity', 0)
        state.daily_pnl = data.get('daily_pnl', 0)
        state.daily_trades = data.get('daily_trades', 0)
        
        lt = data.get('last_trade_time')
        state.last_trade_time = datetime.fromisoformat(lt) if lt else None
        
        state.consecutive_losses = data.get('consecutive_losses', 0)
        state.last_trade_result = data.get('last_trade_result')
        state.state = RiskState(data.get('state', 'NORMAL'))
        state.halt_reason = data.get('halt_reason', '')
        
        cd = data.get('cooldown_until')
        state.cooldown_until = datetime.fromisoformat(cd) if cd else None
        
        state.strategy_states = data.get('strategy_states', {})
        return state


class RiskController:
    """
    统一风控控制器
    
    职责:
    1. 交易前检查 (是否可以交易)
    2. 仓位计算 (建议仓位)
    3. 止损止盈计算
    4. 交易后更新 (记录结果)
    5. 定时检查 (重置/熔断)
    """
    
    def __init__(self, config: RiskConfig = None, state_file: str = None):
        self.config = config or RiskConfig()
        self.state_file = state_file or '/root/.openclaw/workspace/quant/quant/data/risk_state.json'
        self.state = RiskStateData.load(self.state_file)
        
        # 指标缓存
        self._atr: float = 0
        self._last_price: float = 0
    
    def update_equity(self, equity: float):
        """更新权益"""
        self.state.current_equity = equity
        
        # 更新历史高点
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity
        
        self.state.save(self.state_file)
    
    def check_before_trade(self, price: float, size_pct: float = None) -> Dict:
        """
        交易前检查
        
        Returns:
            {
                'allowed': bool,
                'reason': str,
                'max_position_pct': float,  # 允许的最大仓位
                'adjusted_size_pct': float   # 调整后的仓位
            }
        }
        """
        # 检查状态
        if self.state.state == RiskState.HALTON:
            return {
                'allowed': False,
                'reason': f"风控暂停: {self.state.halt_reason}",
                'max_position_pct': 0,
                'adjusted_size_pct': 0
            }
        
        # 检查冷却
        if self.state.state == RiskState.COOLDOWN:
            if self.state.cooldown_until and datetime.now() < self.state.cooldown_until:
                remaining = (self.state.cooldown_until - datetime.now()).seconds // 60
                return {
                    'allowed': False,
                    'reason': f"冷却中，还剩 {remaining} 分钟",
                    'max_position_pct': 0,
                    'adjusted_size_pct': 0
                }
            else:
                # 冷却结束，恢复正常
                self.state.state = RiskState.NORMAL
                self.state.consecutive_losses = 0
        
        # 检查每日交易次数
        if self.state.daily_trades >= self.config.max_daily_trades:
            return {
                'allowed': False,
                'reason': f"已达每日最大交易次数 {self.config.max_daily_trades}",
                'max_position_pct': 0,
                'adjusted_size_pct': 0
            }
        
        # 检查交易间隔
        if self.state.last_trade_time:
            elapsed = (datetime.now() - self.state.last_trade_time).total_seconds()
            if elapsed < self.config.min_trade_interval_seconds:
                return {
                    'allowed': False,
                    'reason': f"交易间隔 {self.config.min_trade_interval_seconds} 秒",
                    'max_position_pct': 0,
                    'adjusted_size_pct': 0
                }
        
        # 计算允许的最大仓位
        max_pct = self._calculate_max_position(price)
        
        # 调整仓位
        adjusted = size_pct
        if size_pct and size_pct > max_pct:
            adjusted = max_pct
        
        return {
            'allowed': True,
            'reason': 'OK',
            'max_position_pct': max_pct,
            'adjusted_size_pct': adjusted or max_pct
        }
    
    def _calculate_max_position(self, price: float) -> float:
        """根据账户状态计算最大允许仓位"""
        # 基础仓位
        max_pct = self.config.max_position_pct
        
        # 如果回撤较大，降低仓位
        if self.state.peak_equity > 0:
            drawdown = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity
            
            if drawdown > 0.10:
                max_pct = min(max_pct, 0.3)  # 回撤 >10% -> 最多 30%
            elif drawdown > 0.05:
                max_pct = min(max_pct, 0.4)  # 回撤 >5% -> 最多 40%
        
        # 连亏降低仓位
        max_pct = max_pct * (1 - 0.1 * self.state.consecutive_losses)
        
        # 不低于最小仓位
        return max(self.config.min_position_pct, max_pct)
    
    def calculate_stop_loss(self, entry_price: float, side: str = 'LONG') -> float:
        """计算止损价"""
        if self.config.use_atr_stop and self._atr > 0:
            # ATR 动态止损
            if side == 'LONG':
                return entry_price - self._atr * self.config.atr_multiplier
            else:
                return entry_price + self._atr * self.config.atr_multiplier
        else:
            # 固定百分比止损
            if side == 'LONG':
                return entry_price * (1 - self.config.stop_loss_pct)
            else:
                return entry_price * (1 + self.config.stop_loss_pct)
    
    def calculate_take_profit(self, entry_price: float, side: str = 'LONG') -> float:
        """计算止盈价"""
        if side == 'LONG':
            return entry_price * (1 + self.config.take_profit_pct)
        else:
            return entry_price * (1 - self.config.take_profit_pct)
    
    def update_atr(self, df: pd.DataFrame, period: int = 14):
        """更新 ATR 指标"""
        if 'high' not in df.columns or 'low' not in df.columns:
            return
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        self._atr = float(atr.iloc[-1]) if len(atr.dropna()) > 0 else 0
        self._last_price = float(close.iloc[-1])
    
    def after_trade(self, pnl: float, trade_time: datetime = None):
        """交易后更新状态"""
        now = trade_time or datetime.now()
        self.state.last_trade_time = now
        self.state.daily_trades += 1
        
        # 更新盈亏
        self.state.daily_pnl += pnl
        
        # 更新连亏
        if pnl > 0:
            self.state.consecutive_losses = 0
            self.state.last_trade_result = 'WIN'
        else:
            self.state.consecutive_losses += 1
            self.state.last_trade_result = 'LOSS'
        
        # 检查是否触发冷却
        if self.state.consecutive_losses >= self.config.max_consecutive_losses:
            self.state.state = RiskState.COOLDOWN
            self.state.cooldown_until = now + timedelta(minutes=self.config.cooldown_minutes)
        
        self.state.save(self.state_file)
    
    def check_daily_reset(self):
        """每日重置检查 (开盘时调用)"""
        now = datetime.now()
        
        # 如果是新的一天，重置日度数据
        if self.state.last_trade_time:
            last_date = self.state.last_trade_time.date()
            if now.date() > last_date:
                self.state.daily_pnl = 0
                self.state.daily_trades = 0
                self.state.save(self.state_file)
    
    def check_risk_limits(self) -> Dict:
        """检查风控限制 (定时调用)"""
        # 检查回撤熔断
        if self.state.peak_equity > 0:
            drawdown = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity
            
            if drawdown >= self.config.max_drawdown_pct:
                self.state.state = RiskState.HALTON
                self.state.halt_reason = f"回撤 {drawdown:.1%} 超过阈值 {self.config.max_drawdown_pct:.1%}"
                self.state.save(self.state_file)
                return {
                    'triggered': True,
                    'type': 'DRAWDOWN',
                    'reason': self.state.halt_reason
                }
        
        # 检查日亏熔断
        if self.state.daily_pnl < 0:
            daily_loss_pct = abs(self.state.daily_pnl) / self.state.peak_equity if self.state.peak_equity > 0 else 0
            
            if daily_loss_pct >= self.config.daily_loss_pct:
                self.state.state = RiskState.HALTON
                self.state.halt_reason = f"日亏 {daily_loss_pct:.1%} 超过阈值 {self.config.daily_loss_pct:.1%}"
                self.state.save(self.state_file)
                return {
                    'triggered': True,
                    'type': 'DAILY_LOSS',
                    'reason': self.state.halt_reason
                }
        
        return {'triggered': False}
    
    def get_status(self) -> Dict:
        """获取风控状态"""
        return {
            'state': self.state.state.value,
            'peak_equity': self.state.peak_equity,
            'current_equity': self.state.current_equity,
            'daily_pnl': self.state.daily_pnl,
            'daily_trades': self.state.daily_trades,
            'consecutive_losses': self.state.consecutive_losses,
            'halt_reason': self.state.halt_reason,
            'cooldown_until': self.state.cooldown_until.isoformat() if self.state.cooldown_until else None,
        }
    
    def reset(self):
        """重置风控状态 (谨慎使用)"""
        self.state = RiskStateData()
        self.state.save(self.state_file)


# 兼容旧接口
class RiskManager:
    """兼容旧 RiskManager 接口"""
    
    def __init__(self, config: RiskConfig = None):
        self.controller = RiskController(config)
    
    def check_risk_limits(self) -> Dict:
        return self.controller.check_risk_limits()
    
    def calculate_position_size(self, capital: float, price: float, risk_pct: float = 0.02) -> float:
        """计算仓位"""
        check = self.controller.check_before_trade(price)
        return capital * risk_pct * check['adjusted_size_pct']
    
    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        self.controller.update_atr(df, period)
        return self.controller._atr
    
    def compute_stop_levels(self, price: float, atr: float, side: str) -> tuple:
        entry = price  # 假设当前价作为参考
        stop = self.controller.calculate_stop_loss(entry, side)
        take = self.controller.calculate_take_profit(entry, side)
        return stop, take


__all__ = [
    'RiskConfig',
    'RiskState',
    'RiskStateData', 
    'RiskController',
    'RiskManager',  # 兼容
]
