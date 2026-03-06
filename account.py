"""
账户协议 - 参考QIFI标准
统一账户数据结构
"""

from datetime import datetime
from typing import Dict, List, Optional
import json


class Account:
    """
    统一账户接口
    
    参考 QIFI 协议设计
    """
    
    def __init__(self, account_id: str, init_cash: float = 100000):
        self.account_id = account_id
        self.init_cash = init_cash
        self.balance = init_cash  # 账户总权益
        self.available = init_cash  # 可用资金
        self.position_value = 0  # 持仓市值
        self.total_value = init_cash  # 总权益
        self.float_pnl = 0  # 浮动盈亏
        self.realized_pnl = 0  # 已实现盈亏
        self.commission = 0  # 手续费
        self.positions: Dict[str, Position] = {}  # 持仓
        self.orders: List[Order] = []  # 订单
        self.trades: List[Trade] = []  # 成交
        self.timestamp = datetime.now()
    
    def update(self, price_data: Dict[str, float]):
        """
        更新账户状态
        
        Args:
            price_data: {symbol: price}
        """
        self.position_value = 0
        self.float_pnl = 0
        
        for symbol, pos in self.positions.items():
            if symbol in price_data:
                pos.update_price(price_data[symbol])
                self.position_value += pos.value
                self.float_pnl += pos.float_pnl
        
        self.total_value = self.balance + self.position_value
    
    def buy(self, symbol: str, price: float, volume: float) -> 'Order':
        """买入开仓"""
        order = Order(
            symbol=symbol,
            direction='long',
            offset='open',
            price=price,
            volume=volume
        )
        self.orders.append(order)
        return order
    
    def sell(self, symbol: str, price: float, volume: float) -> 'Order':
        """卖出平仓"""
        if symbol not in self.positions:
            return None
        
        order = Order(
            symbol=symbol,
            direction='short',
            offset='close',
            price=price,
            volume=volume
        )
        self.orders.append(order)
        return order
    
    def get_position(self, symbol: str) -> Optional['Position']:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "account_id": self.account_id,
            "timestamp": self.timestamp.isoformat(),
            "balance": round(self.balance, 2),
            "available": round(self.available, 2),
            "position_value": round(self.position_value, 2),
            "total_value": round(self.total_value, 2),
            "float_pnl": round(self.float_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "commission": round(self.commission, 2),
            "positions": {s: p.to_dict() for s, p in self.positions.items()}
        }
    
    def to_qifi(self) -> Dict:
        """
        转换为QIFI格式
        
        参考 QUANTAXIS QIFI协议
        """
        return {
            "account": {
                "account_id": self.account_id,
                "broker": "binance",
                "strategy": "quant_v2",
                "init_cash": self.init_cash,
                "balance": self.balance,
                "available": self.available,
                "margin": 0,
                "float_pnl": self.float_pnl,
                "realized_pnl": self.realized_pnl,
                "total_pnl": self.float_pnl + self.realized_pnl,
                "commission": self.commission,
                "timestamp": self.timestamp.isoformat()
            },
            "positions": [p.to_dict() for p in self.positions.values()],
            "orders": len(self.orders),
            "trades": len(self.trades)
        }


class Position:
    """持仓"""
    
    def __init__(self, symbol: str, volume: float = 0, 
                 frozen: float = 0, price: float = 0):
        self.symbol = symbol
        self.volume = volume  # 持仓数量
        self.frozen = frozen  # 冻结数量
        self.price = price  # 持仓成本价
        self.value = 0  # 市值
        self.float_pnl = 0  # 浮动盈亏
        self.open_cost = 0  # 开仓成本
    
    def update_price(self, current_price: float):
        """更新价格"""
        self.value = self.volume * current_price
        self.float_pnl = self.value - self.open_cost
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "volume": self.volume,
            "frozen": self.frozen,
            "price": round(self.price, 2),
            "value": round(self.value, 2),
            "float_pnl": round(self.float_pnl, 2),
            "open_cost": round(self.open_cost, 2)
        }


class Order:
    """订单"""
    
    def __init__(self, symbol: str, direction: str, offset: str,
                 price: float, volume: float):
        self.order_id = ""
        self.symbol = symbol
        self.direction = direction  # long/short
        self.offset = offset  # open/close
        self.price = price
        self.volume = volume
        self.status = "pending"  # pending/filled/cancelled
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "offset": self.offset,
            "price": self.price,
            "volume": self.volume,
            "status": self.status,
            "timestamp": self.timestamp.isoformat()
        }


class Trade:
    """成交"""
    
    def __init__(self, order: Order, trade_price: float, trade_volume: float):
        self.trade_id = ""
        self.order_id = order.order_id
        self.symbol = order.symbol
        self.direction = order.direction
        self.offset = order.offset
        self.price = trade_price
        self.volume = trade_volume
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "offset": self.offset,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat()
        }


# 全局账户实例
_account: Optional[Account] = None


def get_account(account_id: str = "default") -> Account:
    """获取账户实例"""
    global _account
    if _account is None:
        _account = Account(account_id)
    return _account


def save_account(filepath: str = "data/account.json"):
    """保存账户状态"""
    account = get_account()
    with open(filepath, 'w') as f:
        json.dump(account.to_dict(), f, indent=2)


def load_account(filepath: str = "data/account.json") -> Account:
    """加载账户状态"""
    global _account
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        _account = Account(data['account_id'], data.get('init_cash', 100000))
        _account.balance = data.get('balance', 100000)
        # 加载持仓...
        return _account
    except:
        return get_account()


if __name__ == '__main__':
    # 测试
    acc = get_account()
    acc.buy("BTC/USDT", 50000, 0.1)
    print(acc.to_qifi())
