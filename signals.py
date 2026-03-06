"""
信号与订单管理模块
交易信号生成和订单执行
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"   # 限价单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待成交
    FILLED = "FILLED"       # 已成交
    CANCELLED = "CANCELLED" # 已取消
    REJECTED = "REJECTED"   # 已拒绝


class Signal:
    """
    交易信号
    """
    
    def __init__(self, 
                 symbol: str,
                 signal_type: SignalType,
                 price: float = 0,
                 volume: float = 0,
                 reason: str = ""):
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.volume = volume
        self.reason = reason
        self.timestamp = datetime.now()
        self.confidence = 0.5
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "type": self.signal_type.value,
            "price": self.price,
            "volume": self.volume,
            "reason": self.reason,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class Order:
    """
    订单
    """
    
    def __init__(self,
                 symbol: str,
                 direction: str,  # long/short
                 order_type: OrderType,
                 price: float,
                 volume: float):
        self.order_id = ""
        self.symbol = symbol
        self.direction = direction
        self.order_type = order_type
        self.price = price
        self.volume = volume
        self.filled_volume = 0
        self.status = OrderStatus.PENDING
        self.timestamp = datetime.now()
        self.filled_time = None
        self.filled_price = 0
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "type": self.order_type.value,
            "price": self.price,
            "volume": self.volume,
            "filled_volume": self.filled_volume,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "filled_price": self.filled_price
        }


class SignalGenerator:
    """
    信号生成器
    """
    
    def __init__(self, name: str = "signal_generator"):
        self.name = name
        self.strategies = []
        self.signals = []
    
    def add_strategy(self, strategy_func):
        """添加策略"""
        self.strategies.append(strategy_func)
    
    def generate(self, data: Dict, timestamp: datetime = None) -> List[Signal]:
        """
        生成信号
        
        Args:
            data: 市场数据 {symbol: df}
            timestamp: 时间戳
        
        Returns:
            List[Signal]: 信号列表
        """
        signals = []
        
        for strategy in self.strategies:
            try:
                result = strategy(data)
                
                if result:
                    if isinstance(result, dict):
                        signal = Signal(
                            symbol=result.get('symbol', 'default'),
                            signal_type=SignalType(result.get('action', 'HOLD')),
                            price=result.get('price', 0),
                            volume=result.get('volume', 0),
                            reason=result.get('reason', '')
                        )
                        signal.confidence = result.get('confidence', 0.5)
                        signals.append(signal)
                    elif isinstance(result, str):
                        signal = Signal(
                            symbol='default',
                            signal_type=SignalType(result),
                            reason='strategy output'
                        )
                        signals.append(signal)
                        
            except Exception as e:
                print(f"策略执行错误: {e}")
        
        self.signals.extend(signals)
        return signals
    
    def get_latest_signals(self, n: int = 10) -> List[Signal]:
        """获取最新信号"""
        return self.signals[-n:]


class OrderManager:
    """
    订单管理器
    """
    
    def __init__(self):
        self.orders: List[Order] = []
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.cancelled_orders: List[Order] = []
    
    def create_order(self, signal: Signal) -> Order:
        """从信号创建订单"""
        direction = "long" if signal.signal_type == SignalType.BUY else "short"
        
        order = Order(
            symbol=signal.symbol,
            direction=direction,
            order_type=OrderType.MARKET if signal.price == 0 else OrderType.LIMIT,
            price=signal.price,
            volume=signal.volume
        )
        
        order.order_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.orders)}"
        
        self.orders.append(order)
        self.pending_orders.append(order)
        
        return order
    
    def fill_order(self, order_id: str, filled_price: float, filled_volume: float):
        """订单成交"""
        for order in self.pending_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.FILLED
                order.filled_price = filled_price
                order.filled_volume = filled_volume
                order.filled_time = datetime.now()
                
                self.pending_orders.remove(order)
                self.filled_orders.append(order)
                return True
        return False
    
    def cancel_order(self, order_id: str):
        """取消订单"""
        for order in self.pending_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.pending_orders.remove(order)
                self.cancelled_orders.append(order)
                return True
        return False
    
    def get_pending_count(self) -> int:
        """获取待成交订单数"""
        return len(self.pending_orders)
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "total_orders": len(self.orders),
            "pending": len(self.pending_orders),
            "filled": len(self.filled_orders),
            "cancelled": len(self.cancelled_orders)
        }


# 信号转订单示例
def signal_to_order(signal: Signal, price: float, position_pct: float = 0.1) -> Order:
    """
    将信号转换为订单
    """
    if signal.signal_type == SignalType.HOLD:
        return None
    
    # 计算下单量 (简化版)
    from account import get_account
    account = get_account()
    
    if signal.volume > 0:
        volume = signal.volume
    else:
        # 根据仓位比例计算
        value = account.available * position_pct
        volume = value / price if price > 0 else 0
    
    direction = "long" if signal.signal_type == SignalType.BUY else "short"
    
    return Order(
        symbol=signal.symbol,
        direction=direction,
        order_type=OrderType.MARKET,
        price=0,  # 市价单
        volume=volume
    )


# 策略信号函数示例
def rsi_strategy(data: Dict, period: int = 14, oversold: int = 30, overbought: int = 70) -> Dict:
    """
    RSI策略信号
    """
    if 'default' not in data:
        return {'action': 'HOLD'}
    
    df = data['default']
    if len(df) < period + 1:
        return {'action': 'HOLD'}
    
    # 计算RSI
    close = df['close'].values
    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    if rsi < oversold:
        return {'action': 'BUY', 'reason': f'RSI超卖({rsi:.0f})', 'confidence': (30 - rsi) / 30}
    elif rsi > overbought:
        return {'action': 'SELL', 'reason': f'RSI超买({rsi:.0f})', 'confidence': (rsi - 70) / 30}
    
    return {'action': 'HOLD'}


if __name__ == '__main__':
    import numpy as np
    
    # 测试
    gen = SignalGenerator()
    gen.add_strategy(rsi_strategy)
    
    # 模拟数据
    import pandas as pd
    close = np.cumsum(np.random.randn(100)) + 100
    data = {'default': pd.DataFrame({'close': close})}
    
    signals = gen.generate(data)
    for s in signals[-5:]:
        print(f"{s.signal_type.value}: {s.reason}")


# 避免循环导入
import numpy as np
