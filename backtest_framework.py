#!/usr/bin/env python3
"""
策略回测框架
统一的回测接口，支持多策略
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 10000
    commission: float = 0.001      # 手续费
    slippage: float = 0.0005     # 滑点
    leverage: float = 1.0
    risk_free_rate: float = 0.02


@dataclass
class Trade:
    """交易记录"""
    time: str
    symbol: str
    side: str  # BUY, SELL
    price: float
    quantity: float
    value: float
    commission: float
    slippage: float
    pnl: float = 0


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0
    
    @property
    def value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def pnl(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity


class Strategy(ABC):
    """策略基类"""
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成信号
        
        Returns:
            Series: 1=BUY, -1=SELL, 0=HOLD
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class Backtester:
    """
    统一回测框架
    
    支持:
    - 多策略
    - 多市场
    - 精确成本
    - 绩效分析
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        
        self.strategy: Optional[Strategy] = None
        self.data: Optional[pd.DataFrame] = None
        
        # 状态
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        
        # 统计
        self.stats: Dict = {}
    
    def set_strategy(self, strategy: Strategy):
        """设置策略"""
        self.strategy = strategy
    
    def set_data(self, data: pd.DataFrame):
        """设置数据"""
        self.data = data
    
    def reset(self):
        """重置状态"""
        self.cash = self.config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
    
    def run(self, data: pd.DataFrame = None, strategy: Strategy = None) -> Dict:
        """
        运行回测
        
        Args:
            data: K线数据
            strategy: 策略 (如果不设置则用self.strategy)
        
        Returns:
            回测统计
        """
        # 设置
        if data is not None:
            self.data = data
        if strategy is not None:
            self.strategy = strategy
        
        if self.data is None or self.strategy is None:
            return {}
        
        # 重置
        self.reset()
        
        # 生成信号
        signals = self.strategy.generate_signals(self.data)
        
        # 遍历执行
        for i in range(len(self.data)):
            row = self.data.iloc[i]
            timestamp = str(row.name) if hasattr(row.name, 'strftime') else str(i)
            price = row.get('close', 0)
            
            if price == 0:
                continue
            
            # 更新持仓价格
            for pos in self.positions.values():
                pos.current_price = price
            
            # 信号
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # 执行交易
            if signal == 1 and not self.positions:
                self._buy(timestamp, price)
            elif signal == -1 and self.positions:
                self._sell(timestamp, price)
记录权益
            equity = self.cash + sum(p.value            
            #  for p in self.positions.values())
            self.equity_curve.append(equity)
        
        # 平仓
        if self.positions:
            last_price = self.data.iloc[-1]['close']
            self._sell(str(len(self.data)), last_price)
        
        # 计算统计
        self.stats = self._calculate_stats()
        
        return self.stats
    
    def _buy(self, timestamp: str, price: float):
        """买入"""
        # 计算成本
        commission = price * self.config.commission
        slippage = price * self.config.slippage
        exec_price = price * (1 + self.config.slippage)
        
        value = self.cash * 0.95  # 95%仓位
        quantity = value / exec_price
        
        if quantity > 0:
            cost = quantity * exec_price + commission
            
            if cost <= self.cash:
                self.cash -= cost
                
                self.positions['BTC'] = Position(
                    symbol='BTC',
                    quantity=quantity,
                    avg_price=exec_price,
                    current_price=exec_price
                )
                
                self.trades.append(Trade(
                    time=timestamp,
                    symbol='BTC',
                    side='BUY',
                    price=exec_price,
                    quantity=quantity,
                    value=cost,
                    commission=commission,
                    slippage=slippage
                ))
    
    def _sell(self, timestamp: str, price: float):
        """卖出"""
        if not self.positions:
            return
        
        pos = self.positions.get('BTC')
        if not pos:
            return
        
        commission = price * self.config.commission
        slippage = price * self.config.slippage
        exec_price = price * (1 - self.config.slippage)
        
        proceeds = pos.quantity * exec_price - commission
        
        # 计算盈亏
        pnl = proceeds - (pos.quantity * pos.avg_price)
        
        self.cash += proceeds
        
        self.trades.append(Trade(
            time=timestamp,
            symbol='BTC',
            side='SELL',
            price=exec_price,
            quantity=pos.quantity,
            value=proceeds,
            commission=commission,
            slippage=slippage,
            pnl=pnl
        ))
        
        del self.positions['BTC']
    
    def _calculate_stats(self) -> Dict:
        """计算统计"""
        if not self.equity_curve:
            return {}
        
        equity = np.array(self.equity_curve)
        returns = np.diff(equity) / equity[:-1]
        
        # 基本统计
        initial = equity[0]
        final = equity[-1]
        total_return = (final - initial) / initial
        
        # 年化
        n_days = len(equity)
        ann_return = (1 + total_return) ** (252 / n_days) - 1
        
        # 波动率
        vol = np.std(returns) * np.sqrt(252)
        
        # 夏普
        sharpe = (ann_return - self.config.risk_free_rate) / vol if vol > 0 else 0
        
        # 回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_dd = abs(np.min(drawdown))
        
        # 交易统计
        buy_trades = [t for t in self.trades if t.side == 'BUY']
        sell_trades = [t for t in self.trades if t.side == 'SELL']
        
        wins = [t for t in sell_trades if t.pnl > 0]
        losses = [t for t in sell_trades if t.pnl <= 0]
        
        win_rate = len(wins) / len(sell_trades) if sell_trades else 0
        
        return {
            'initial_capital': initial,
            'final_equity': final,
            'total_return': total_return,
            'annualized_return': ann_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_trades': len(self.trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'equity_curve': equity.tolist()
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("策略回测框架")
    print("=" * 50)
    
    # 示例策略
    class RSIStrategy(Strategy):
        def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
            self.period = period
            self.overbought = overbought
            self.oversold = oversold
        
        def get_name(self) -> str:
            return f"RSI({self.period},{self.overbought},{self.oversold})"
        
        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            # 计算RSI
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 信号
            signals = pd.Series(0, index=data.index)
            signals[rsi < self.oversold] = 1   # 买入
            signals[rsi > self.overbought] = -1  # 卖出
            
            return signals
    
    # 生成测试数据
    np.random.seed(42)
    n = 200
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    
    data = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.uniform(1000, 5000, n)
    })
    
    # 创建回测
    config = BacktestConfig(initial_capital=10000)
    backtester = Backtester(config)
    
    # 设置策略
    strategy = RSIStrategy(14, 70, 30)
    backtester.set_strategy(strategy)
    
    # 运行
    print("\n🚀 运行回测...")
    stats = backtester.run(data)
    
    # 结果
    print(f"\n📊 回测结果:")
    print(f"  初始资金: ${stats['initial_capital']:,.2f}")
    print(f"  最终权益: ${stats['final_equity']:,.2f}")
    print(f"  总收益: {stats['total_return']:.2%}")
    print(f"  年化收益: {stats['annualized_return']:.2%}")
    print(f"  夏普比率: {stats['sharpe_ratio']:.2f}")
    print(f"  最大回撤: {stats['max_drawdown']:.2%}")
    print(f"  交易次数: {stats['total_trades']}")
    print(f"  胜率: {stats['win_rate']:.1%}")
