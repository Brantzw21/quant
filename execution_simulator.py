#!/usr/bin/env python3
"""
执行模拟器
处理手续费、滑点、成交逻辑
"""

class ExecutionSimulator:
    """执行模拟器"""
    
    def __init__(self,
                 commission: float = 0.0004,  # 手续费 0.04%
                 slippage: float = 0.0005,    # 滑点 0.05%
                 min_notional: float = 5):     # 最小成交金额
        self.commission = commission
        self.slippage = slippage
        self.min_notional = min_notional
    
    def simulate_buy(self, price: float, quantity: float) -> dict:
        """
        模拟买入
        
        滑点: 买入时价格上浮
        手续费: 买入时扣除
        """
        # 价格上浮 (滑点)
        slippage_price = price * (1 + self.slippage)
        
        # 计算成交金额
        notional = slippage_price * quantity
        
        # 检查最小成交额
        if notional < self.min_notional:
            return {
                'success': False,
                'reason': f'金额不足，最小 {self.min_notional} USDT',
                'price': price,
                'quantity': 0,
                'commission': 0,
                'slippage': 0
            }
        
        # 计算手续费
        commission_cost = notional * self.commission
        
        # 总成本
        total_cost = notional + commission_cost
        
        return {
            'success': True,
            'price': slippage_price,
            'quantity': quantity,
            'notional': notional,
            'commission': commission_cost,
            'total_cost': total_cost,
            'slippage': (slippage_price - price) / price * 100,
            'action': 'BUY'
        }
    
    def simulate_sell(self, price: float, quantity: float) -> dict:
        """
        模拟卖出
        
        滑点: 卖出时价格下浮
        手续费: 卖出时扣除
        """
        # 价格下浮 (滑点)
        slippage_price = price * (1 - self.slippage)
        
        # 计算成交金额
        notional = slippage_price * quantity
        
        # 检查最小成交额
        if notional < self.min_notional:
            return {
                'success': False,
                'reason': f'金额不足，最小 {self.min_notional} USDT',
                'price': price,
                'quantity': 0,
                'commission': 0,
                'slippage': 0
            }
        
        # 计算手续费
        commission_cost = notional * self.commission
        
        # 净收入
        net_proceeds = notional - commission_cost
        
        return {
            'success': True,
            'price': slippage_price,
            'quantity': quantity,
            'notional': notional,
            'commission': commission_cost,
            'net_proceeds': net_proceeds,
            'slippage': (price - slippage_price) / price * 100,
            'action': 'SELL'
        }
    
    def calculate_fee(self, notional: float) -> float:
        """计算手续费"""
        return notional * self.commission
    
    def apply_slippage(self, price: float, side: str) -> float:
        """应用滑点"""
        if side == 'BUY':
            return price * (1 + self.slippage)
        else:  # SELL
            return price * (1 - self.slippage)


if __name__ == "__main__":
    sim = ExecutionSimulator(commission=0.0004, slippage=0.0005)
    
    # 测试买入
    result = sim.simulate_buy(50000, 0.01)
    print("=== 买入测试 ===")
    print(f"价格: ${result['price']:.2f}")
    print(f"数量: {result['quantity']} BTC")
    print(f"成交额: ${result['notional']:.2f}")
    print(f"手续费: ${result['commission']:.4f}")
    print(f"总成本: ${result['total_cost']:.2f}")
    print(f"滑点: {result['slippage']:.3f}%")
    
    # 测试卖出
    result = sim.simulate_sell(55000, 0.01)
    print("\n=== 卖出测试 ===")
    print(f"价格: ${result['price']:.2f}")
    print(f"数量: {result['quantity']} BTC")
    print(f"成交额: ${result['notional']:.2f}")
    print(f"手续费: ${result['commission']:.4f}")
    print(f"净收入: ${result['net_proceeds']:.2f}")
    print(f"滑点: {result['slippage']:.3f}%")
