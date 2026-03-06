"""
合约交易适配器 - 让现有策略支持期货合约
==========================================

改动点:
1. 杠杆管理
2. 双向交易 (多/空)
3. 严格风控
4. 合约标的对接
"""

from binance_broker import BinanceBroker
from typing import Dict, Any


class FuturesAdapter:
    """
    期货合约适配器
    
    让现有策略可以直接用于合约交易
    """
    
    def __init__(self, broker: BinanceBroker, config: Dict):
        self.broker = broker
        self.config = config
        
        # 合约特有参数
        self.leverage = config.get('leverage', 3)  # 默认3倍杠杆
        self.position_type = config.get('position_type', 'LONG')  # LONG/SHORT
        
        # 设置杠杆
        self._set_leverage()
    
    def _set_leverage(self):
        """设置杠杆倍数"""
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        for symbol in symbols:
            try:
                self.broker.client.futures_change_leverage(
                    symbol=symbol,
                    leverage=self.leverage
                )
                print(f"设置 {symbol} 杠杆: {self.leverage}X")
            except Exception as e:
                print(f"设置杠杆失败: {e}")
    
    def process_signal(self, symbol: str, signal: str, price: float) -> bool:
        """
        处理交易信号
        
        信号格式:
        - "BUY" / "LONG" -> 做多
        - "SELL" / "SHORT" -> 做空  
        - "CLOSE" -> 平仓
        - "HOLD" -> 持有
        
        Returns:
            是否执行成功
        """
        positions = self.broker.get_positions()
        current_position = positions.get(symbol, {}).get("quantity", 0)
        
        # 信号处理
        if signal in ["BUY", "LONG"]:
            if current_position < 0:  # 持有空头，先平仓
                self._close_position(symbol)
            if current_position <= 0:  # 无持仓或多头，开多仓
                return self._open_long(symbol, price)
                
        elif signal in ["SELL", "SHORT"]:
            if current_position > 0:  # 持有多头，先平仓
                self._close_position(symbol)
            if current_position >= 0:  # 无持仓或空头，开空仓
                return self._open_short(symbol, price)
                
        elif signal == "CLOSE":
            return self._close_position(symbol)
        
        return True
    
    def _open_long(self, symbol: str, price: float) -> bool:
        """开多仓"""
        balance = self.broker.get_balance()
        # 可用资金 * 杠杆 * 仓位比例
        max_notional = balance * self.leverage * self.config.get('position_pct', 0.3)
        quantity = int(max_notional / price)
        
        if quantity < 1:
            print(f"资金不足，无法开多: {symbol}")
            return False
        
        try:
            order = self.broker.place_order(
                symbol=symbol,
                side="BUY",
                quantity=quantity,
            )
            print(f"开多成功: {symbol} @ {price}, 数量: {quantity}")
            return True
        except Exception as e:
            print(f"开多失败: {e}")
            return False
    
    def _open_short(self, symbol: str, price: float) -> bool:
        """开空仓"""
        balance = self.broker.get_balance()
        max_notional = balance * self.leverage * self.config.get('position_pct', 0.3)
        quantity = int(max_notional / price)
        
        if quantity < 1:
            print(f"资金不足，无法开空: {symbol}")
            return False
        
        try:
            order = self.broker.place_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity,
            )
            print(f"开空成功: {symbol} @ {price}, 数量: {quantity}")
            return True
        except Exception as e:
            print(f"开空失败: {e}")
            return False
    
    def _close_position(self, symbol: str) -> bool:
        """平仓"""
        try:
            order = self.broker.close_position(symbol)
            if order:
                print(f"平仓成功: {symbol}")
                return True
            return False
        except Exception as e:
            print(f"平仓失败: {e}")
            return False
    
    def check_risk(self, symbol: str) -> bool:
        """
        风控检查
        
        合约需要更严格的风控:
        1. 仓位不能太大
        2. 亏损不能超过限制
        3. 需要设置止盈止损
        """
        positions = self.broker.get_positions()
        
        if symbol not in positions:
            return True  # 无持仓，通过
        
        pos = positions[symbol]
        
        # 检查未实现亏损
        unrealized_pnl = pos.get("unrealized_pnl", 0)
        entry_price = pos.get("entry_price", 0)
        
        if entry_price > 0:
            pnl_pct = unrealized_pnl / (entry_price * abs(pos["quantity"]))
            
            # 止损 -5%
            if pnl_pct < -0.05:
                print(f"触发止损: {symbol}, 亏损 {pnl_pct:.2%}")
                self._close_position(symbol)
                return False
            
            # 止盈 +15%
            if pnl_pct > 0.15:
                print(f"触发止盈: {symbol}, 盈利 {pnl_pct:.2%}")
                self._close_position(symbol)
                return False
        
        return True


def create_futures_executor(broker: BinanceBroker, config: Dict) -> FuturesAdapter:
    """创建合约执行器"""
    return FuturesAdapter(broker, config)


if __name__ == "__main__":
    # 测试
    import os
    from binance_broker import BinanceBroker
    
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret_key = os.getenv("BINANCE_SECRET_KEY", "")
    
    broker = BinanceBroker(api_key, secret_key, testnet=True)
    
    config = {
        "leverage": 3,
        "position_pct": 0.3,  # 只用30%仓位
        "symbols": ["BTCUSDT", "ETHUSDT"]
    }
    
    executor = create_futures_executor(broker, config)
    
    # 测试开多
    price = broker.get_price("BTCUSDT")
    print(f"\n当前BTC价格: {price}")
    
    # 信号测试
    print("\n--- 测试信号: BUY ---")
    executor.process_signal("BTCUSDT", "BUY", price)
