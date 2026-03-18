#!/usr/bin/env python3
"""
回测信号与持仓数据结构
统一信号格式，支持置信度和分批操作
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class Side(Enum):
    """交易方向"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class SignalType(Enum):
    """信号类型"""
    ENTRY = "ENTRY"      # 建仓
    ADD = "ADD"          # 加仓
    REDUCE = "REDUCE"    # 减仓
    EXIT = "EXIT"        # 平仓
    HOLD = "HOLD"        # 持有


@dataclass
class Signal:
    """
    交易信号
    
    Attributes:
        side: 交易方向 (LONG/SHORT/FLAT)
        confidence: 置信度 0-1
        signal_type: 信号类型
        reason: 信号原因/说明
        timestamp: 信号时间
        size_pct: 建议仓位比例 0-1 (用于分批建仓)
    """
    side: Side = Side.FLAT
    confidence: float = 0.5
    signal_type: SignalType = SignalType.HOLD
    reason: str = ""
    timestamp: Optional[datetime] = None
    size_pct: float = 0.0  # 建议仓位比例
    
    def is_buy(self) -> bool:
        return self.side == Side.LONG and self.confidence >= 0.5
    
    def is_sell(self) -> bool:
        return self.side == Side.FLAT or self.confidence < 0.3
    
    def to_numeric(self) -> int:
        """转换为传统信号格式 (1/-1/0)"""
        if self.side == Side.LONG and self.confidence >= 0.6:
            return 1
        elif self.side == Side.SHORT and self.confidence >= 0.6:
            return -1
        return 0


@dataclass
class PositionLayer:
    """
    持仓层 (支持网格/分批建仓)
    
    用于记录每一层建仓的信息
    """
    layer_id: int                     # 层 ID (0=首批, 1=加仓层, etc.)
    side: Side                         # 方向
    quantity: float                   # 数量
    avg_price: float                   # 平均价格
    entry_time: str                    # 建仓时间
    stop_loss: Optional[float] = None  # 止损价
    take_profit: Optional[float] = None # 止盈价
    current_price: float = 0.0        # 当前价格
    
    @property
    def value(self) -> float:
        return self.quantity * self.current_price
    
    def pnl(self, current_price: float = None) -> float:
        if current_price is not None:
            self.current_price = current_price
        if self.side == Side.LONG:
            return (self.current_price - self.avg_price) * self.quantity
        elif self.side == Side.SHORT:
            return (self.avg_price - self.current_price) * self.quantity
        return 0
    
    def pnl_pct(self, current_price: float = None) -> float:
        if current_price is not None:
            self.current_price = current_price
        if self.avg_price == 0:
            return 0
        if self.side == Side.LONG:
            return (self.current_price - self.avg_price) / self.avg_price
        elif self.side == Side.SHORT:
            return (self.avg_price - self.current_price) / self.avg_price
        return 0


@dataclass
class Position:
    """
    多空双向持仓管理器
    
    支持:
    - 多层持仓 (网格/分批)
    - 多空双向
    - 动态止损止盈
    """
    symbol: str
    layers: List[PositionLayer] = field(default_factory=list)
    
    @property
    def is_long(self) -> bool:
        return any(l.side == Side.LONG for l in self.layers)
    
    @property
    def is_short(self) -> bool:
        return any(l.side == Side.SHORT for l in self.layers)
    
    @property
    def is_flat(self) -> bool:
        return len(self.layers) == 0
    
    @property
    def total_quantity(self) -> float:
        return sum(l.quantity for l in self.layers)
    
    @property
    def avg_price(self) -> float:
        """加权平均价格"""
        total = sum(l.quantity * l.avg_price for l in self.layers)
        qty = self.total_quantity
        return total / qty if qty > 0 else 0
    
    def add_layer(self, layer: PositionLayer):
        """添加新持仓层"""
        self.layers.append(layer)
    
    def remove_layer(self, layer_id: int) -> PositionLayer:
        """移除指定持仓层"""
        for i, layer in enumerate(self.layers):
            if layer.layer_id == layer_id:
                return self.layers.pop(i)
        return None
    
    def get_value(self, current_price: float) -> float:
        return self.total_quantity * current_price
    
    def get_pnl(self, current_price: float) -> float:
        return sum(layer.pnl(current_price) for layer in self.layers)
    
    def get_pnl_pct(self, current_price: float) -> float:
        if self.avg_price == 0:
            return 0
        return self.get_pnl(current_price) / (self.avg_price * self.total_quantity) if self.total_quantity > 0 else 0


# 兼容旧代码 - 作为函数
def make_buy_signal(confidence: float = 1.0) -> Signal:
    return Signal(side=Side.LONG, confidence=confidence, signal_type=SignalType.ENTRY)

def make_sell_signal(confidence: float = 1.0) -> Signal:
    return Signal(side=Side.FLAT, confidence=confidence, signal_type=SignalType.EXIT)

def make_hold_signal(confidence: float = 0.5) -> Signal:
    return Signal(side=Side.FLAT, confidence=confidence, signal_type=SignalType.HOLD)


__all__ = [
    'Side',
    'SignalType', 
    'Signal',
    'PositionLayer',
    'Position',
]
