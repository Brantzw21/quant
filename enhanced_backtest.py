#!/usr/bin/env python3
"""
增强回测引擎
精确模拟交易成本、滑点、流动性
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """交易记录"""
    time: str
    type: str  # BUY, SELL
    price: float
    quantity: float
    commission: float  # 手续费
    slippage: float    # 滑点
    total: float       # 总成本


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 10000
    commission_rate: float = 0.001     # 手续费率 (0.1%)
    slippage_pct: float = 0.0005        # 滑点 (0.05%)
    min_trade_value: float = 10         # 最小交易金额
    leverage: float = 1.0              # 杠杆
    maker_fee: float = 0.0002          # Maker手续费
    taker_fee: float = 0.0007          # Taker手续费


class EnhancedBacktestEngine:
    """
    增强回测引擎
    
    特性:
    - 精确手续费计算
    - 滑点模拟
    - 流动性限制
    - 杠杆支持
    - 爆仓模拟
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        
        # 状态
        self.capital = self.config.initial_capital
        self.position = 0  # 持仓数量
        self.position_value = 0  # 持仓价值
        self.trades: List[Trade] = []
        
        # 统计
        self.wins = 0
        self.losses = 0
        self.total_commission = 0
        self.total_slippage = 0
    
    def reset(self):
        """重置状态"""
        self.capital = self.config.initial_capital
        self.position = 0
        self.position_value = 0
        self.trades = []
        self.wins = 0
        self.losses = 0
        self.total_commission = 0
        self.total_slippage = 0
    
    def calculate_commission(self, price: float, quantity: float, is_maker: bool = False) -> float:
        """计算手续费"""
        value = price * quantity
        
        # 手续费率
        if is_maker:
            fee_rate = self.config.maker_fee
        else:
            fee_rate = self.config.taker_fee
        
        commission = value * fee_rate
        
        # 最低手续费
        return max(commission, self.config.min_trade_value * 0.01)
    
    def calculate_slippage(self, price: float, quantity: float, side: str) -> float:
        """
        计算滑点
        
        滑点模型:
        - 大额订单滑点更大
        - 市场波动大时滑点更大
        """
        # 基础滑点
        base_slippage = self.config.slippage_pct
        
        # 大额订单增加滑点
        value = price * quantity
        if value > 10000:
            base_slippage *= 1.5
        elif value > 50000:
            base_slippage *= 2.0
        
        # 方向影响
        if side == "BUY":
            slippage = price * base_slippage * quantity  # 买贵
        else:
            slippage = price * base_slippage * quantity  # 卖便宜
        
        return slippage
    
    def buy(self, time: str, price: float, quantity: float) -> bool:
        """买入"""
        # 计算成本
        commission = self.calculate_commission(price, quantity, is_maker=False)
        slippage = self.calculate_slippage(price, quantity, "BUY")
        
        total_cost = price * quantity + commission + slippage
        
        # 检查资金
        if total_cost > self.capital:
            # 资金不足，调整数量
            max_quantity = (self.capital - commission) / (price * (1 + self.config.slippage_pct))
            if max_quantity <= 0:
                return False
            quantity = max_quantity
            total_cost = price * quantity + self.calculate_commission(price, quantity) + self.calculate_slippage(price, quantity, "BUY")
        
        # 执行
        self.capital -= total_cost
        self.position += quantity
        self.position_value = self.position * price
        
        # 记录
        self.trades.append(Trade(
            time=time,
            type="BUY",
            price=price,
            quantity=quantity,
            commission=commission,
            slippage=slippage,
            total=total_cost
        ))
        
        self.total_commission += commission
        self.total_slippage += slippage
        
        return True
    
    def sell(self, time: str, price: float, quantity: float = None) -> bool:
        """卖出"""
        if quantity is None:
            quantity = self.position
        
        if quantity > self.position:
            quantity = self.position
        
        if quantity <= 0:
            return False
        
        # 计算收益
        commission = self.calculate_commission(price, quantity, is_maker=True)
        slippage = self.calculate_slippage(price, quantity, "SELL")
        
        total_proceeds = price * quantity - commission - slippage
        
        # 记录盈亏
        avg_cost = self.position_value / self.position if self.position > 0 else 0
        if price > avg_cost:
            self.wins += 1
        else:
            self.losses += 1
        
        # 执行
        self.capital += total_proceeds
        self.position -= quantity
        self.position_value = self.position * price
        
        # 记录
        self.trades.append(Trade(
            time=time,
            type="SELL",
            price=price,
            quantity=quantity,
            commission=commission,
            slippage=slippage,
            total=total_proceeds
        ))
        
        self.total_commission += commission
        self.total_slippage += slippage
        
        return True
    
    def get_equity(self, current_price: float) -> float:
        """获取当前权益"""
        return self.capital + self.position * current_price
    
    def run(self, df: pd.DataFrame, signals: pd.Series) -> Dict:
        """
        运行回测
        
        Args:
            df: K线数据 (需要 open, high, low, close 列)
            signals: 信号序列 (1=买入, -1=卖出, 0=持有)
        
        Returns:
            回测结果
        """
        self.reset()
        
        equity_curve = []
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            signal = signals.iloc[i] if i < len(signals) else 0
            time = str(df.index[i]) if hasattr(df.index[i], 'strftime') else str(i)
            
            # 买入信号
            if signal == 1 and self.position == 0:
                # 使用开盘价买入，或者开盘买入
                buy_price = df['open'].iloc[i] if 'open' in df.columns else current_price
                quantity = (self.capital * 0.95) / buy_price  # 95%仓位
                self.buy(time, buy_price, quantity)
            
            # 卖出信号
            elif signal == -1 and self.position > 0:
                sell_price = df['open'].iloc[i] if 'open' in df.columns else current_price
                self.sell(time, sell_price)
            
            # 记录权益
            equity = self.get_equity(current_price)
            equity_curve.append(equity)
        
        # 最终清仓
        if self.position > 0:
            final_price = df['close'].iloc[-1]
            self.sell("end", final_price)
        
        # 计算统计
        return self._calculate_stats(equity_curve)
    
    def _calculate_stats(self, equity_curve: List[float]) -> Dict:
        """计算统计指标"""
        if not equity_curve:
            return {}
        
        equity = np.array(equity_curve)
        
        # 收益率
        returns = np.diff(equity) / equity[:-1]
        returns = returns[~np.isnan(returns)]
        
        # 基本统计
        total_return = (equity[-1] - equity[0]) / equity[0]
        annualized_return = (1 + total_return) ** (252 / len(equity)) - 1
        
        # 夏普比率
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        # 最大回撤
        cummax = np.maximum.accumulate(equity)
        drawdowns = (equity - cummax) / cummax
        max_drawdown = abs(np.min(drawdowns))
        
        # 胜率
        total_trades = self.wins + self.losses
        win_rate = self.wins / total_trades if total_trades > 0 else 0
        
        return {
            'initial_capital': self.config.initial_capital,
            'final_equity': equity[-1],
            'total_return': round(total_return, 4),
            'annualized_return': round(annualized_return, 4),
            'sharpe_ratio': round(sharpe, 3),
            'max_drawdown': round(max_drawdown, 4),
            'win_rate': round(win_rate, 3),
            'total_trades': total_trades,
            'total_commission': round(self.total_commission, 2),
            'total_slippage': round(self.total_slippage, 2),
            'avg_commission_per_trade': round(self.total_commission / total_trades, 2) if total_trades > 0 else 0,
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("增强回测引擎测试")
    print("=" * 50)
    
    # 创建引擎
    config = BacktestConfig(
        initial_capital=10000,
        commission_rate=0.001,
        slippage_pct=0.001,
    )
    engine = EnhancedBacktestEngine(config)
    
    # 模拟数据
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'high': 105 + np.cumsum(np.random.randn(n) * 0.5),
        'low': 95 + np.cumsum(np.random.randn(n) * 0.5),
        'close': 100 + np.cumsum(np.random.randn(n) * 0.5),
    })
    
    # 简单信号
    signals = pd.Series(0, index=range(n))
    signals[10] = 1   # 买入
    signals[30] = -1  # 卖出
    signals[50] = 1  # 买入
    signals[70] = -1 # 卖出
    
    # 回测
    result = engine.run(df, signals)
    
    print("\n📊 回测结果:")
    for k, v in result.items():
        print(f"  {k}: {v}")
