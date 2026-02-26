"""
资金/仓位管理模块 - Position Sizing
=====================================

功能:
- 根据账户规模计算仓位
- 风险预算分配
- 多标的资金管理

作者: AI量化系统
"""

from typing import Dict, List
from dataclasses import dataclass
import math


@dataclass
class PositionSize:
    """仓位结果"""
    quantity: int          # 股数/份额
    amount: float          # 金额
    position_pct: float   # 仓位占比


class PositionSizer:
    """
    仓位管理器
    
    支持:
    - 固定金额
    - 固定比例
    - 波动率调整
    - 风险预算
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 默认参数
        self.max_position_pct = config.get('max_position_pct', 0.95)  # 单标的最大仓位
        self.max_total_pct = config.get('max_total_pct', 1.0)         # 总仓位上限
        self.min_cash_reserve = config.get('min_cash_reserve', 100)   # 最小现金保留
        
        # 风控参数
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)  # 单笔最大风险2%
        self.max_daily_risk = config.get('max_daily_risk', 0.05)          # 日内最大风险5%
    
    def calculate_position(self, 
                         capital: float,
                         price: float,
                         method: str = "fixed_ratio",
                         params: Dict = None) -> PositionSize:
        """
        计算仓位
        
        Args:
            capital: 总资金
            price: 当前价格
            method: 计算方法
            params: 其他参数
        
        Returns:
            PositionSize
        """
        params = params or {}
        
        if method == "fixed_amount":
            return self._fixed_amount(capital, price, params)
        elif method == "fixed_ratio":
            return self._fixed_ratio(capital, price, params)
        elif method == "volatility_based":
            return self._volatility_based(capital, price, params)
        elif method == "kelly":
            return self._kelly(capital, price, params)
        else:
            return self._fixed_ratio(capital, price, {})
    
    def _fixed_amount(self, capital: float, price: float, 
                     params: Dict) -> PositionSize:
        """固定金额"""
        amount = params.get('amount', capital * 0.5)
        amount = min(amount, capital * self.max_position_pct)
        
        quantity = int(amount / price)
        
        return PositionSize(
            quantity=quantity,
            amount=quantity * price,
            position_pct=quantity * price / capital
        )
    
    def _fixed_ratio(self, capital: float, price: float,
                    params: Dict) -> PositionSize:
        """固定比例"""
        ratio = params.get('ratio', 0.5)
        ratio = min(ratio, self.max_position_pct)
        
        amount = capital * ratio
        quantity = int(amount / price)
        
        return PositionSize(
            quantity=quantity,
            amount=quantity * price,
            position_pct=ratio
        )
    
    def _volatility_based(self, capital: float, price: float,
                         params: Dict) -> PositionSize:
        """
        波动率调整仓位
        
        原理:
        - 波动大 → 仓位小
        - 波动小 → 仓位大
        """
        # 目标波动率
        target_vol = params.get('target_vol', 0.15)  # 15%
        
        # 当前波动率 (年化)
        current_vol = params.get('volatility', 0.30)
        
        # 波动率比率
        vol_ratio = target_vol / current_vol if current_vol > 0 else 1
        
        # 调整仓位
        ratio = min(vol_ratio, self.max_position_pct)
        
        amount = capital * ratio
        quantity = int(amount / price)
        
        return PositionSize(
            quantity=quantity,
            amount=quantity * price,
            position_pct=ratio
        )
    
    def _kelly(self, capital: float, price: float,
               params: Dict) -> PositionSize:
        """
        Kelly公式仓位
        
        公式: K% = W - (1-W)/R
        W = 胜率, R = 盈亏比
        """
        win_rate = params.get('win_rate', 0.5)
        win_loss_ratio = params.get('win_loss_ratio', 1.5)
        
        # Kelly公式
        kelly_pct = win_rate - (1 - win_rate) / win_loss_ratio
        
        # 半Kelly更保守
        kelly_pct = kelly_pct * 0.5
        
        # 限制范围
        kelly_pct = max(0, min(kelly_pct, self.max_position_pct))
        
        amount = capital * kelly_pct
        quantity = int(amount / price)
        
        return PositionSize(
            quantity=quantity,
            amount=quantity * price,
            position_pct=kelly_pct
        )
    
    def calculate_multi_positions(self,
                                capital: float,
                                prices: Dict[str, float],
                                weights: Dict[str, float] = None) -> Dict[str, PositionSize]:
        """
        多标的仓位计算
        
        Args:
            capital: 总资金
            prices: {symbol: price}
            weights: {symbol: weight} 如果为空则等权
        
        Returns:
            {symbol: PositionSize}
        """
        if weights is None:
            # 等权
            n = len(prices)
            weights = {s: 1.0/n for s in prices}
        
        # 归一化权重
        total_weight = sum(weights.values())
        weights = {s: w/total_weight for s, w in weights.items()}
        
        # 计算各标的仓位
        result = {}
        available_capital = capital * self.max_total_pct
        
        for symbol, price in prices.items():
            weight = weights.get(symbol, 0)
            amount = available_capital * weight
            amount = min(amount, capital * self.max_position_pct)
            
            quantity = int(amount / price)
            
            result[symbol] = PositionSize(
                quantity=quantity,
                amount=quantity * price,
                position_pct=quantity * price / capital
            )
        
        return result
    
    def check_risk_limits(self,
                         current_positions: Dict[str, float],
                         daily_pnl: float,
                         capital: float) -> Dict[str, bool]:
        """
        检查风险限额
        
        Returns:
            {limit_name: 是否通过}
        """
        # 日亏损检查
        daily_loss_ratio = abs(daily_pnl) / capital if daily_pnl < 0 else 0
        
        return {
            'daily_loss_ok': daily_loss_ratio < self.max_daily_risk,
            'position_limit_ok': True,  # 简化检查
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置
    config = {
        'max_position_pct': 0.95,
        'max_total_pct': 1.0,
        'min_cash_reserve': 100,
    }
    
    sizer = PositionSizer(config)
    
    # 1. 固定比例仓位
    result = sizer.calculate_position(
        capital=1500,
        price=100,
        method="fixed_ratio",
        params={'ratio': 0.5}
    )
    print(f"固定比例: 买入 {result.quantity} 股, 占比 {result.position_pct:.1%}")
    
    # 2. Kelly仓位
    result = sizer.calculate_position(
        capital=1500,
        price=100,
        method="kelly",
        params={'win_rate': 0.55, 'win_loss_ratio': 1.5}
    )
    print(f"Kelly: 买入 {result.quantity} 股, 占比 {result.position_pct:.1%}")
    
    # 3. 多标的
    prices = {'SPY': 450, 'QQQ': 380, 'AAPL': 175}
    positions = sizer.calculate_multi_positions(1500, prices)
    print("\n多标的仓位:")
    for symbol, pos in positions.items():
        print(f"  {symbol}: {pos.quantity}股 ({pos.position_pct:.1%})")
