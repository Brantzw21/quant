"""
Binance 期货Broker
支持币安期货测试网和实盘
"""
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BinanceBroker:
    """币安期货Broker"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = True):
        """
        初始化Binance Broker
        
        Args:
            api_key: API密钥（优先从环境变量读取）
            secret_key: 密钥（优先从环境变量读取）
            testnet: 是否使用测试网
        """
        # 优先从环境变量读取
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.secret_key = secret_key or os.getenv("BINANCE_SECRET_KEY")
        self.testnet = testnet
        
        if not self.api_key or not self.secret_key:
            raise ValueError("API密钥未设置，请设置 BINANCE_API_KEY 和 BINANCE_SECRET_KEY 环境变量")
        
        # 创建客户端
        self.client = Client(self.api_key, self.secret_key, testnet=testnet)
        
        logger.info(f"Binance Broker 初始化完成，测试网: {testnet}")
    
    def get_account(self) -> Dict[str, Any]:
        """获取账户信息"""
        try:
            account = self.client.futures_account()
            return {
                "total_balance": float(account.get("totalWalletBalance", 0)),
                "available_balance": float(account.get("availableBalance", 0)),
                "total_unrealized_pnl": float(account.get("totalUnrealizedProfit", 0)),
            }
        except BinanceAPIException as e:
            logger.error(f"获取账户失败: {e}")
            raise
    
    def get_positions(self) -> Dict[str, Any]:
        """获取当前持仓"""
        try:
            positions = self.client.futures_position_information()
            result = {}
            for pos in positions:
                symbol = pos["symbol"]
                qty = float(pos.get("positionAmt", 0))
                if qty != 0:  # 只保留有持仓的
                    result[symbol] = {
                        "quantity": qty,
                        "entry_price": float(pos.get("entryPrice", 0)),
                        "unrealized_pnl": float(pos.get("unrealizedProfit", 0)),
                        "leverage": int(pos.get("leverage", 1)),
                    }
            return result
        except BinanceAPIException as e:
            logger.error(f"获取持仓失败: {e}")
            raise
    
    def get_balance(self) -> float:
        """获取可用余额"""
        account = self.client.futures_account()
        return float(account.get("availableBalance", 0))
    
    def place_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        quantity: float,
        order_type: str = "MARKET",
        price: float = None,
    ) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 合约 symbol，如 BTCUSDT
            side: BUY 或 SELL
            quantity: 数量
            order_type: 订单类型 (MARKET, LIMIT)
            price: 价格（限价单需要）
        """
        try:
            if order_type == "MARKET":
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                )
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    timeInForce="GTC",
                    price=price,
                )
            
            logger.info(f"下单成功: {order}")
            return order
        except BinanceAPIException as e:
            logger.error(f"下单失败: {e}")
            raise
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """平仓"""
        positions = self.get_positions()
        if symbol not in positions:
            logger.warning(f"无持仓: {symbol}")
            return None
        
        qty = positions[symbol]["quantity"]
        side = "SELL" if qty > 0 else "BUY"
        
        return self.place_order(
            symbol=symbol,
            side=side,
            quantity=abs(qty),
        )
    
    def get_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except BinanceAPIException as e:
            logger.error(f"获取价格失败: {e}")
            raise


def create_broker(testnet: bool = True) -> BinanceBroker:
    """创建Binance Broker的便捷函数"""
    return BinanceBroker(testnet=testnet)


if __name__ == "__main__":
    # 测试
    broker = create_broker(testnet=True)
    print(f"账户: {broker.get_account()}")
    print(f"余额: {broker.get_balance()}")
