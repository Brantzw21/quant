#!/usr/bin/env python3
"""
仓位计算器
根据账户权益和风险参数计算仓位
"""

class PositionSizer:
    """仓位管理器"""
    
    def __init__(self, 
                 risk_per_trade: float = 0.2,  # 每笔风险比例
                 min_position: float = 100,     # 最小仓位价值
                 max_position_pct: float = 0.5): # 最大持仓比例
        self.risk_per_trade = risk_per_trade  # 0.2 = 20%
        self.min_position = min_position
        self.max_position_pct = max_position_pct
    
    def calculate_size(self, 
                       balance: float, 
                       entry_price: float, 
                       stop_loss_pct: float = None) -> float:
        """
        计算仓位数量
        
        Args:
            balance: 账户余额
            entry_price: 入场价格
            stop_loss_pct: 止损比例 (可选)
        
        Returns:
            仓位数量
        """
        # 方式1: 固定比例仓位
        position_value = balance * self.risk_per_trade
        
        # 方式2: 如果有止损，按风险敞口计算
        if stop_loss_pct and stop_loss_pct > 0:
            risk_amount = balance * self.risk_per_trade  # 愿意承受的风险
            # 仓位 = 风险金额 / 止损距离
            position_value = risk_amount / stop_loss_pct
        
        # 确保在最小仓位以上
        if position_value < self.min_position:
            position_value = self.min_position
        
        # 转换为数量
        quantity = position_value / entry_price
        
        return quantity
    
    def calculate_position_pct(self, position_value: float, total_equity: float) -> float:
        """计算持仓占比"""
        if total_equity <= 0:
            return 0
        return position_value / total_equity
    
    def can_open_position(self, 
                          current_position_pct: float,
                          new_position_pct: float) -> bool:
        """检查是否可以开仓"""
        return (current_position_pct + new_position_pct) <= self.max_position_pct


if __name__ == "__main__":
    ps = PositionSizer(risk_per_trade=0.2)
    
    # 测试
    balance = 10000
    price = 50000
    
    size = ps.calculate_size(balance, price)
    print(f"余额: {balance}, 价格: {price}")
    print(f"仓位数量: {size:.6f} BTC")
    print(f"仓位价值: ${size * price:.2f}")
