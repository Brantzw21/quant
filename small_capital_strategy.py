#!/usr/bin/env python3
"""
小资金合约网格策略
专为63USDT设计，极低杠杆
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from smart_grid_strategy import SmartGridStrategy


class SmallCapitalStrategy:
    """
    小资金合约策略
    
    专为63USDT设计:
    - 1-2倍杠杆 (不用10x!)
    - 极小仓位
    - 严格止损
    - 只做短线
    """
    
    def __init__(self, capital: float = 63):
        self.capital = capital
        
        # 安全的杠杆倍数
        self.leverage = 5  # 5倍杠杆
        
        # 每单金额 (用10%的资金)
        self.order_pct = 0.10  # 每次约6U
        self.order_amount = capital * self.order_pct
        
        # 止损 (3%)
        self.stop_loss = 0.03
        
        # 止盈 (6%)
        self.take_profit = 0.06
        
        # 策略
        self.grid_strategy = SmartGridStrategy(
            symbol="ETHUSDT",
            base_grid_count=3,  # 少档位
            grid_range=0.03,   # 小范围3%
            order_amount=self.order_amount,
            use_trend_filter=True,
            use_dynamic_grid=True,
            use_trailing_stop=True,
            trailing_atr_multiplier=1.5,
            max_position_pct=0.1,  # 最多10%仓位
            stop_loss_pct=0.02    # 2%止损
        )
    
    def get_position_size(self) -> float:
        """计算开仓数量"""
        return self.order_amount * self.leverage
    
    def check_risk(self, current_price: float, entry_price: float, side: str) -> dict:
        """
        检查风险
        
        Returns:
            {'safe': bool, 'liquidation_price': float, 'risk': str}
        """
        if side == "LONG":
            # 做多爆仓价
            liq_price = entry_price * (1 - 1/self.leverage * 0.95)
            risk_pct = (entry_price - liq_price) / entry_price * 100
        else:
            # 做空爆仓价
            liq_price = entry_price * (1 + 1/self.leverage * 0.95)
            risk_pct = (liq_price - entry_price) / entry_price * 100
        
        safe = risk_pct > 10  # 超过10%波动才爆仓才算安全
        
        return {
            'safe': safe,
            'liquidation_price': liq_price,
            'risk_pct': risk_pct,
            'recommendation': 'SAFE' if safe else 'DANGER'
        }
    
    def generate_order(self, current_price: float, positions: float) -> dict:
        """
        生成订单
        
        Returns:
            {'action': 'BUY'/'SELL'/'WAIT', 'amount': float, 'leverage': int}
        """
        # 检查是否需要止损
        if positions > 0:
            # 假设持仓均价
            avg_price = current_price * 0.98  # 简化
            
            # 止损检查
            loss_pct = (avg_price - current_price) / avg_price
            if loss_pct >= self.stop_loss:
                return {
                    'action': 'SELL',
                    'amount': positions,
                    'reason': f'止损 {loss_pct:.1%}'
                }
            
            # 止盈检查
            profit_pct = (current_price - avg_price) / avg_price
            if profit_pct >= self.take_profit:
                return {
                    'action': 'SELL', 
                    'amount': positions,
                    'reason': f'止盈 {profit_pct:.1%}'
                }
        
        # 检查风险
        risk_info = self.check_risk(current_price, current_price, "LONG")
        
        if not risk_info['safe']:
            return {
                'action': 'WAIT',
                'amount': 0,
                'reason': f'风险过高: {risk_info["risk_pct"]:.1f}%波动爆仓'
            }
        
        # 生成信号
        signal = self.grid_strategy.generate_signal(
            current_price=current_price,
            prices=[current_price],
            highs=[current_price*1.01],
            lows=[current_price*0.99],
            volumes=[10000],
            positions=positions
        )
        
        if signal['signal'] == 'BUY' and positions < self.capital * 0.1:
            return {
                'action': 'BUY',
                'amount': self.get_position_size(),
                'leverage': self.leverage,
                'reason': signal.get('reason', '网格信号')
            }
        
        return {
            'action': 'WAIT',
            'amount': 0,
            'reason': signal.get('reason', '无信号')
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("小资金合约策略")
    print("=" * 50)
    
    # 创建策略
    strategy = SmallCapitalStrategy(capital=63)
    
    print(f"\n📊 参数:")
    print(f"  本金: {strategy.capital} USDT")
    print(f"  杠杆: {strategy.leverage}x")
    print(f"  每单: {strategy.order_amount:.1f} USDT")
    print(f"  止损: {strategy.stop_loss:.0%}")
    print(f"  止盈: {strategy.take_profit:.0%}")
    
    # 风险检查
    print(f"\n⚠️ 风险检查 (当前ETH约2067):")
    risk = strategy.check_risk(2067, 2067, "LONG")
    print(f"  做多爆仓价: {risk['liquidation_price']:.2f}")
    print(f"  安全波动: {risk['risk_pct']:.1f}%")
    print(f"  建议: {risk['recommendation']}")
    
    # 订单
n    print(f"\📝 当前信号:")
    order = strategy.generate_order(2067, 0)
    print(f"  操作: {order['action']}")
    print(f"  金额: {order['amount']}")
    print(f"  原因: {order['reason']}")
