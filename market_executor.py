#!/usr/bin/env python3
"""
统一市场执行器
支持多市场：Binance (数字货币), IBKR (美股), A股(开发中)
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from typing import Optional, Dict, List
from enum import Enum


class MarketType(Enum):
    CRYPTO = "crypto"      # 数字货币
    US_STOCK = "us_stock"  # 美股
    CN_STOCK = "cn_stock"  # A股


class MarketExecutor:
    """
    统一市场执行器
    
    使用示例:
        executor = MarketExecutor(MarketType.US_STOCK)
        executor.connect()
        price = executor.get_price("AAPL")
        order_id = executor.buy("AAPL", 10)
    """
    
    def __init__(self, market: MarketType, paper: bool = True):
        self.market = market
        self.paper = paper
        self.broker = None
        self._connect()
    
    def _connect(self):
        """根据市场类型连接对应的broker"""
        if self.market == MarketType.CRYPTO:
            self._connect_crypto()
        elif self.market == MarketType.US_STOCK:
            self._connect_us_stock()
        elif self.market == MarketType.CN_STOCK:
            self._connect_cn_stock()
    
    def _connect_crypto(self):
        """连接Binance"""
        try:
            from brokers.binance_broker import BinanceBroker
            self.broker = BinanceBroker()
            print("✅ 已连接 Binance (数字货币)")
        except Exception as e:
            print(f"❌ Binance连接失败: {e}")
    
    def _connect_us_stock(self):
        """连接IBKR"""
        try:
            from brokers.ibkr_broker import IBKRBroker, IBKRConfig
            config = IBKRConfig(is_paper=self.paper)
            self.broker = IBKRBroker(config)
            if self.broker.connect():
                print(f"✅ 已连接 IBKR (美股, Paper={self.paper})")
            else:
                print("❌ IBKR连接失败")
        except ImportError:
            print("❌ ib_insync 未安装: pip install ib_insync")
        except Exception as e:
            print(f"❌ IBKR连接失败: {e}")
    
    def _connect_cn_stock(self):
        """连接A股 (待开发)"""
        print("⚠️ A股实盘接口开发中")
        self.broker = None
    
    def get_price(self, symbol: str) -> float:
        """获取当前价格"""
        if not self.broker:
            return 0
        
        if self.market == MarketType.CRYPTO:
            # Binance
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            ticker = client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        
        elif self.market == MarketType.US_STOCK:
            return self.broker.get_stock_price(symbol)
        
        return 0
    
    def buy(self, symbol: str, quantity: int, limit_price: Optional[float] = None) -> str:
        """买入"""
        if not self.broker:
            return ""
        
        if self.market == MarketType.CRYPTO:
            return self._buy_crypto(symbol, quantity)
        elif self.market == MarketType.US_STOCK:
            return self._buy_us_stock(symbol, quantity, limit_price)
        
        return ""
    
    def sell(self, symbol: str, quantity: int, limit_price: Optional[float] = None) -> str:
        """卖出"""
        if not self.broker:
            return ""
        
        if self.market == MarketType.CRYPTO:
            return self._sell_crypto(symbol, quantity)
        elif self.market == MarketType.US_STOCK:
            return self._sell_us_stock(symbol, quantity, limit_price)
        
        return ""
    
    def _buy_crypto(self, symbol: str, quantity: float) -> str:
        """Binance买入"""
        from config import API_KEY, SECRET_KEY, TESTNET, LEVERAGE
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        # 市价单
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.FUTURE_ORDER_TYPE_MARKET,
            quantity=quantity,
            leverage=LEVERAGE
        )
        return str(order['orderId'])
    
    def _sell_crypto(self, symbol: str, quantity: float) -> str:
        """Binance卖出"""
        from config import API_KEY, SECRET_KEY, TESTNET, LEVERAGE
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.FUTURE_ORDER_TYPE_MARKET,
            quantity=quantity,
            leverage=LEVERAGE
        )
        return str(order['orderId'])
    
    def _buy_us_stock(self, symbol: str, quantity: int, limit_price: Optional[float] = None) -> str:
        """IBKR买入"""
        if limit_price:
            return self.broker.place_limit_order(symbol, quantity, "BUY", limit_price)
        else:
            return self.broker.place_market_order(symbol, quantity, "BUY")
    
    def _sell_us_stock(self, symbol: str, quantity: int, limit_price: Optional[float] = None) -> str:
        """IBKR卖出"""
        if limit_price:
            return self.broker.place_limit_order(symbol, quantity, "SELL", limit_price)
        else:
            return self.broker.place_market_order(symbol, quantity, "SELL")
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        if not self.broker:
            return []
        
        if self.market == MarketType.US_STOCK:
            return self.broker.get_positions()
        
        # Binance 持仓
        from config import API_KEY, SECRET_KEY, TESTNET
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        positions = client.futures_position_information(symbol="BTCUSDT")
        return positions
    
    def get_account_balance(self) -> Dict:
        """获取账户余额"""
        if not self.broker:
            return {}
        
        if self.market == MarketType.US_STOCK:
            return self.broker.get_account_info()
        
        # Binance
        from config import API_KEY, SECRET_KEY, TESTNET
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        account = client.futures_account()
        
        return {
            'balance': float(account['totalWalletBalance']),
            'available': float(account['availableBalance']),
            'margin': float(account['totalMarginBalance'])
        }
    
    def disconnect(self):
        """断开连接"""
        if self.broker and hasattr(self.broker, 'disconnect'):
            self.broker.disconnect()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 测试美股
    print("=" * 50)
    print("测试 MarketExecutor (美股)")
    print("=" * 50)
    
    executor = MarketExecutor(MarketType.US_STOCK, paper=True)
    
    # 获取价格
    price = executor.get_price("SPY")
    print(f"SPY 价格: ${price}")
    
    # 获取账户
    balance = executor.get_account_balance()
    print(f"账户: {balance}")
    
    # 断开
    executor.disconnect()
