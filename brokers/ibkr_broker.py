"""
IBKR (盈透证券) 券商对接模块
=============================

功能:
- 连接IBKR TWS/API
- 获取实时行情
- 下单交易
- 持仓同步

安装: pip install ib_insync

作者: AI量化系统
"""

from ib_insync import *
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class IBKRConfig:
    """IBKR配置"""
    host: str = "127.0.0.1"
    port: int = 7497  # TWS demo: 7497, paper: 7496
    clientId: int = 1
    is_paper: bool = True  # 是否使用模拟账户


class IBKRBroker:
    """
    IBKR 券商对接
    
    支持:
    - 实时行情
    - 市价/限价单
    - 持仓查询
    - 账户信息
    """
    
    def __init__(self, config: IBKRConfig = None):
        self.config = config or IBKRConfig()
        self.ib = IB()
        self.connected = False
    
    def connect(self) -> bool:
        """连接IBKR"""
        try:
            port = 7496 if self.config.is_paper else 7497
            
            self.ib.connect(
                self.config.host,
                port,
                self.config.clientId
            )
            
            self.connected = True
            print(f"✅ IBKR连接成功 (Paper: {self.config.is_paper})")
            return True
            
        except Exception as e:
            print(f"❌ IBKR连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
    
    def get_stock_price(self, symbol: str) -> float:
        """获取股票价格"""
        if not self.connected:
            return 0
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(1)
        
        return ticker.last or ticker.close or 0
    
    def get_quote(self, symbol: str) -> Dict:
        """获取完整报价"""
        if not self.connected:
            return {}
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(1)
        
        return {
            'symbol': symbol,
            'bid': ticker.bid,
            'ask': ticker.ask,
            'last': ticker.last,
            'close': ticker.close,
            'volume': ticker.volume,
            'high': ticker.high,
            'low': ticker.low,
        }
    
    def place_market_order(self, symbol: str, quantity: int, action: str) -> str:
        """
        市价单
        
        Args:
            symbol: 股票代码 (如 'AAPL')
            quantity: 数量
            action: 'BUY' 或 'SELL'
        
        Returns:
            orderId
        """
        if not self.connected:
            return ""
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        order = MarketOrder(action, quantity)
        
        trade = self.ib.placeOrder(contract, order)
        
        # 等待成交
        self.ib.sleep(1)
        
        if trade.orderStatus.status == 'Filled':
            return str(trade.orderStatus.orderId)
        
        return ""
    
    def place_limit_order(self, symbol: str, quantity: int, action: str, 
                         limit_price: float) -> str:
        """限价单"""
        if not self.connected:
            return ""
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        order = LimitOrder(action, quantity, limit_price)
        
        trade = self.ib.placeOrder(contract, order)
        
        self.ib.sleep(1)
        
        return str(trade.orderStatus.orderId)
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        if not self.connected:
            return []
        
        positions = self.ib.positions()
        
        result = []
        for pos in positions:
            result.append({
                'symbol': pos.contract.symbol,
                'quantity': pos.position,
                'avgCost': pos.avgCost,
                'marketValue': pos.marketValue,
            })
        
        return result
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        if not self.connected:
            return {}
        
        account = self.ib.accountSummary()
        
        info = {}
        for a in account:
            if a.tag in ['NetLiquidation', 'BuyingPower', 'Cash', 
                        'GrossPositionValue', 'SMA']:
                info[a.tag] = float(a.value)
        
        return info
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.connected:
            return False
        
        try:
            for order in self.ib.orders():
                if str(order.orderId) == order_id:
                    self.ib.cancelOrder(order)
                    return True
        except:
            pass
        
        return False
    
    def get_historical_data(self, symbol: str, duration: str = "1 Y",
                           bar_size: str = "1 day") -> List[Dict]:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            duration: 数据时长 ('1 D', '1 W', '1 M', '1 Y')
            bar_size: K线周期 ('1 min', '5 min', '1 hour', '1 day')
        """
        if not self.connected:
            return []
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        bars = self.ib.reqHistoricalData(
            contract,
            '',
            duration,
            bar_size,
            'TRADES',
            False
        )
        
        result = []
        for bar in bars:
            result.append({
                'date': bar.date.strftime('%Y-%m-%d'),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
            })
        
        return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 连接IBKR (模拟账户)
    config = IBKRConfig(is_paper=True)
    broker = IBKRBroker(config)
    
    if broker.connect():
        # 获取账户信息
        info = broker.get_account_info()
        print("账户信息:", info)
        
        # 获取持仓
        positions = broker.get_positions()
        print("持仓:", positions)
        
        # 获取历史数据
        bars = broker.get_historical_data('SPY', '1 Y', '1 day')
        print(f"SPY 1年数据: {len(bars)} 条")
        
        # 断开
        broker.disconnect()
