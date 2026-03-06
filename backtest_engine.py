#!/usr/bin/env python3
"""
回测引擎 - 分层架构
========================
backtest_engine    - 主控
     ↓
strategy_agent     - 策略信号
     ↓
risk_manager      - 风控
     ↓
position_sizer    - 仓位计算
     ↓
execution_simulator - 执行模拟
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
import json
import numpy as np
import pandas as pd

# 导入子模块
from position_sizer import PositionSizer
from execution_simulator import ExecutionSimulator


class RiskManager:
    """风控管理器 - ATR 动态止盈止损"""
    
    def __init__(self,
                 max_position_pct: float = 0.5,   # 最大持仓比例
                 max_daily_trades: int = 10,       # 日内最大交易次数
                 max_drawdown_pct: float = 0.2,    # 最大回撤比例
                 atr_multiplier: float = 1.5):     # ATR 倍数
        self.max_position_pct = max_position_pct
        self.max_daily_trades = max_daily_trades
        self.max_drawdown_pct = max_drawdown_pct
        self.atr_multiplier = atr_multiplier
        
        self.daily_trade_count = 0
        self.peak_equity = 0
        self.trades_today = []
    
    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ATR (Average True Range)
        
        TR = max(H-L, |H-PC|, |L-PC|)
        ATR = TR 的均值
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算 TR
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr.iloc[-1]
    
    def compute_stop_levels(self, price: float, atr: float, side: str) -> tuple:
        """
        计算止盈止损价位
        
        Args:
            price: 当前价格
            atr: ATR 值
            side: LONG 或 SHORT
        
        Returns:
            (stop_loss, take_profit)
        """
        if side == "LONG":
            # 多头: 止损在价格下方 1.5x ATR，止盈在上方 3x ATR
            stop_loss = price - atr * self.atr_multiplier
            take_profit = price + atr * self.atr_multiplier * 2
        else:  # SHORT
            # 空头: 止损在价格上方 1.5x ATR，止盈在下方 3x ATR
            stop_loss = price + atr * self.atr_multiplier
            take_profit = price - atr * self.atr_multiplier * 2
        
        return stop_loss, take_profit
    
    def check_stop_take(self, price: float, entry: float, side: str, 
                       stop_loss: float, take_profit: float) -> tuple:
        """
        检查是否触发止盈止损
        
        Returns:
            (triggered: bool, exit_type: str)
        """
        if side == "LONG":
            if price <= stop_loss:
                return True, "STOP_LOSS"
            if price >= take_profit:
                return True, "TAKE_PROFIT"
        else:  # SHORT
            if price >= stop_loss:
                return True, "STOP_LOSS"
            if price <= take_profit:
                return True, "TAKE_PROFIT"
        
        return False, None
    
    def check_position_limit(self, current_pct: float, new_pct: float) -> bool:
        """检查持仓限制"""
        return (current_pct + new_pct) <= self.max_position_pct
    
    def check_drawdown(self, current_equity: float, initial_equity: float) -> bool:
        """检查回撤限制"""
        if self.peak_equity == 0:
            self.peak_equity = initial_equity
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        return drawdown < self.max_drawdown_pct
    
    def check_daily_trades(self) -> bool:
        """检查日内交易次数"""
        return self.daily_trade_count < self.max_daily_trades
    
    def record_trade(self):
        """记录交易"""
        self.daily_trade_count += 1
    
    def reset_daily(self):
        """重置日内计数"""
        self.daily_trade_count = 0


class StrategyAgent:
    """策略代理 - 调用信号生成"""
    
    def __init__(self, strategy_func: Callable = None):
        self.strategy_func = strategy_func
        self.last_signal = None
    
    def generate_signal(self, data: pd.DataFrame) -> Dict:
        """生成信号
        
        返回格式支持:
        - BUY/SELL/HOLD (旧格式)
        - LONG/SHORT/HOLD (新格式)
        """
        if self.strategy_func:
            signal = self.strategy_func(data)
            # 兼容转换
            if signal.get('signal') == 'BUY':
                signal['signal'] = 'LONG'
            elif signal.get('signal') == 'SELL':
                signal['signal'] = 'SHORT'
            return signal
        
        # 默认返回 HOLD
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'reason': 'no strategy'
        }


class BacktestEngine:
    """
    回测引擎 - 主控
    
    架构:
    ┌──────────────┐
    │ backtest_engine (主控) │
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │ strategy_agent (策略)  │
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │ risk_manager (风控)    │
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │ position_sizer (仓位)  │
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │ execution_sim (执行)   │
    └──────────────┘
    """
    
    def __init__(self, 
                 initial_cash: float = 100000,
                 commission: float = 0.0004,    # 手续费 0.04%
                 slippage: float = 0.0005,       # 滑点 0.05%
                 position_pct: float = 0.2):    # 仓位比例 20%
        # 核心组件
        self.position_sizer = PositionSizer(risk_per_trade=position_pct)
        self.execution_sim = ExecutionSimulator(commission=commission, slippage=slippage)
        self.risk_manager = RiskManager()
        self.strategy_agent = StrategyAgent()
        
        # 账户状态
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0  # 持仓数量
        self.position_value = 0  # 持仓价值
        
        # 历史记录
        self.equity_curve = []
        self.trades = []
        self.signals = []
        
        # 统计
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0
    
    def set_strategy(self, strategy_func: Callable):
        """设置策略函数"""
        self.strategy_agent.strategy_func = strategy_func
    
    @property
    def total_equity(self) -> float:
        """总权益 = 现金 + 持仓价值"""
        return self.cash + self.position_value
    
    @property
    def position_pct(self) -> float:
        """持仓比例"""
        if self.total_equity <= 0:
            return 0
        return self.position_value / self.total_equity
    
    def buy(self, price: float, quantity: float = None, 
            stop_loss_pct: float = None) -> Dict:
        """买入"""
        # 计算仓位
        if quantity is None:
            quantity = self.position_sizer.calculate_size(
                self.total_equity, price, stop_loss_pct
            )
        
        # 风控检查
        new_pct = (price * quantity) / self.total_equity
        if not self.risk_manager.check_position_limit(self.position_pct, new_pct):
            return {'success': False, 'reason': 'position limit'}
        
        if not self.risk_manager.check_drawdown(self.total_equity, self.initial_cash):
            return {'success': False, 'reason': 'drawdown limit'}
        
        # 执行模拟
        result = self.execution_sim.simulate_buy(price, quantity)
        
        if not result['success']:
            return result
        
        # 检查现金
        if self.cash < result['total_cost']:
            return {'success': False, 'reason': 'insufficient cash'}
        
        # 执行
        self.cash -= result['total_cost']
        self.position += quantity
        self.position_value = self.position * price
        
        # 记录
        self.risk_manager.record_trade()
        self.trades.append({
            'type': 'BUY',
            'price': result['price'],
            'quantity': quantity,
            'commission': result['commission'],
            'equity': self.total_equity
        })
        self.total_commission += result['commission']
        
        return {'success': True, **result}
    
    def sell(self, price: float, quantity: float = None) -> Dict:
        """卖出"""
        if self.position <= 0:
            return {'success': False, 'reason': 'no position'}
        
        # 卖出全部或指定数量
        if quantity is None:
            quantity = self.position
        
        quantity = min(quantity, self.position)
        
        # 执行模拟
        result = self.execution_sim.simulate_sell(price, quantity)
        
        if not result['success']:
            return result
        
        # 计算盈亏
        avg_entry = self.get_avg_entry_price()
        pnl = (price - avg_entry) * quantity - result['commission']
        
        # 执行
        self.cash += result['net_proceeds']
        self.position -= quantity
        self.position_value = self.position * price
        
        # 记录
        self.trades.append({
            'type': 'SELL',
            'price': result['price'],
            'quantity': quantity,
            'commission': result['commission'],
            'pnl': pnl,
            'equity': self.total_equity
        })
        self.total_commission += result['commission']
        
        # 统计
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        return {'success': True, **result}
    
    def get_avg_entry_price(self) -> float:
        """获取平均入场价"""
        if self.position <= 0:
            return 0
        # 简化：取最后一次买入价
        for trade in reversed(self.trades):
            if trade['type'] in ['BUY', 'entry']:
                return trade['price']
        return 0
    
    def run(self, data: pd.DataFrame, use_atr: bool = True) -> Dict:
        """
        运行回测 - ATR 动态止盈止损版
        
        Args:
            data: K线数据 (需包含 high, low, close)
            use_atr: 是否使用 ATR 动态止盈止损 (默认 True)
        """
        print(f"开始回测: {len(data)} 条数据")
        print(f"初始资金: ${self.initial_cash:.2f}")
        print(f"手续费: {self.execution_sim.commission*100:.2f}%")
        print(f"滑点: {self.execution_sim.slippage*100:.3f}%")
        print(f"仓位比例: {self.position_sizer.risk_per_trade*100:.0f}%")
        print(f"止盈止损: {'ATR 动态' if use_atr else '固定百分比'}")
        print("-" * 50)
        
        # 当前持仓信息
        current_pos = None  # {side, entry, qty, stop, take}
        
        for i in range(50, len(data)):  # 需要足够数据计算指标
            # 获取当前价格
            sub_df = data.iloc[:i+1]
            current_price = sub_df['close'].iloc[-1]
            
            # 计算 ATR (如果启用)
            atr = None
            if use_atr:
                atr = self.risk_manager.compute_atr(sub_df)
            
            # 更新持仓价值
            self.position_value = self.position * current_price
            
            # 检查止盈止损 (如果持有仓位)
            if current_pos:
                side = current_pos['side']
                entry = current_pos['entry']
                stop = current_pos['stop']
                take = current_pos['take']
                
                # 检查是否触发
                triggered, exit_type = self.risk_manager.check_stop_take(
                    current_price, entry, side, stop, take
                )
                
                if triggered:
                    # 执行卖出
                    result = self.execution_sim.simulate_sell(current_price, current_pos['qty'])
                    
                    if result['success']:
                        # 计算盈亏
                        if side == "LONG":
                            pnl = (result['price'] - entry) * current_pos['qty'] - result['commission']
                        else:
                            pnl = (entry - result['price']) * current_pos['qty'] - result['commission']
                        
                        print(f"[{exit_type}] 价格: {current_price:.2f}, 入场: {entry:.2f}, PnL: {pnl:.2f}")
                        
                        self.cash += result['net_proceeds']
                        self.position = 0
                        self.position_value = 0
                        
                        # 记录交易
                        self.trades.append({
                            'type': 'exit',
                            'side': side,
                            'entry': entry,
                            'exit': result['price'],
                            'qty': current_pos['qty'],
                            'pnl': pnl,
                            'exit_type': exit_type,
                            'commission': result['commission']
                        })
                        
                        # 统计
                        if pnl > 0:
                            self.winning_trades += 1
                        else:
                            self.losing_trades += 1
                        
                        self.total_commission += result['commission']
                        current_pos = None
            
            # 如果没有持仓，生成信号
            if current_pos is None:
                signal = self.strategy_agent.generate_signal(sub_df)
                self.signals.append({
                    'idx': i,
                    'signal': signal.get('signal'),
                    'confidence': signal.get('confidence'),
                    'price': current_price
                })
                
                # 开仓信号
                if signal.get('signal') in ["LONG", "SHORT"] and signal.get('confidence', 0) >= 0.6:
                    side = signal['signal']
                    
                    # 计算仓位
                    qty = self.position_sizer.size(self.total_equity, current_price)
                    
                    # 执行价格 (含滑点)
                    if side == "LONG":
                        fill_price = current_price * (1 + self.execution_sim.slippage)
                    else:
                        fill_price = current_price * (1 - self.execution_sim.slippage)
                    
                    # 计算手续费
                    notional = fill_price * qty
                    commission = notional * self.execution_sim.commission
                    total_cost = notional + commission
                    
                    # 检查现金
                    if self.cash < total_cost:
                        print(f"[现金不足] 需要: {total_cost:.2f}, 拥有: {self.cash:.2f}")
                        continue
                    
                    # 计算止盈止损 (ATR 动态)
                    if use_atr and atr:
                        stop, take = self.risk_manager.compute_stop_levels(fill_price, atr, side)
                    else:
                        # 固定百分比
                        if side == "LONG":
                            stop = fill_price * 0.97  # 3% 止损
                            take = fill_price * 1.08  # 8% 止盈
                        else:
                            stop = fill_price * 1.03
                            take = fill_price * 0.92
                    
                    # 执行买入
                    self.cash -= total_cost
                    self.position = qty
                    self.position_value = qty * fill_price
                    
                    # 记录持仓
                    current_pos = {
                        'side': side,
                        'entry': fill_price,
                        'qty': qty,
                        'stop': stop,
                        'take': take
                    }
                    
                    print(f"[开仓 {side}] 价格: {fill_price:.2f}, 数量: {qty:.4f}, 止损: {stop:.2f}, 止盈: {take:.2f}")
                    
                    # 记录交易
                    self.trades.append({
                        'type': 'entry',
                        'side': side,
                        'price': fill_price,
                        'qty': qty,
                        'commission': commission
                    })
                    
                    self.total_commission += commission
            
            # 记录权益
            self.equity_curve.append({
                'idx': i,
                'equity': self.total_equity,
                'position': self.position,
                'cash': self.cash
            })
        
        # 最终平仓
        if current_pos:
            final_price = data.iloc[-1]['close']
            result = self.execution_sim.simulate_sell(final_price, current_pos['qty'])
            if result['success']:
                self.cash += result['net_proceeds']
                print(f"[最终平仓] 价格: {final_price:.2f}")
        
        return self.get_report()
        # 最终平仓
        if self.position > 0:
            final_price = data.iloc[-1]['close']
            self.sell(final_price)
            print(f"[最终平仓] 价格: {final_price:.2f}")
        
        return self.get_report()
    
    def get_report(self) -> Dict:
        """生成报告"""
        total_return = (self.total_equity - self.initial_cash) / self.initial_cash * 100
        total_trades = len([t for t in self.trades if t['type'] == 'SELL'])
        
        winrate = 0
        if total_trades > 0:
            winrate = self.winning_trades / total_trades * 100
        
        # 计算最大回撤
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0] if equity_values else self.initial_cash
        max_dd = 0
        for v in equity_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        
        report = {
            'initial_cash': self.initial_cash,
            'final_equity': self.total_equity,
            'total_return_pct': total_return,
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'winrate_pct': winrate,
            'max_drawdown_pct': max_dd * 100,
            'total_commission': self.total_commission,
            'final_position': self.position
        }
        
        print("\n" + "=" * 50)
        print("========== 回测报告 ==========")
        print("=" * 50)
        print(f"初始资金:     ${report['initial_cash']:.2f}")
        print(f"最终权益:     ${report['final_equity']:.2f}")
        print(f"总收益:       {report['total_return_pct']:.2f}%")
        print(f"交易次数:     {report['total_trades']}")
        print(f"胜率:         {report['winrate_pct']:.1f}%")
        print(f"最大回撤:     {report['max_drawdown_pct']:.2f}%")
        print(f"总手续费:     ${report['total_commission']:.2f}")
        print("=" * 50)
        
        return report
    
    def save_results(self, filename: str = "backtest_results.json"):
        """保存结果"""
        results = {
            'report': self.get_report(),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"结果已保存到: {filename}")


if __name__ == "__main__":
    # 简单测试
    engine = BacktestEngine(
        initial_cash=10000,
        commission=0.0004,
        slippage=0.0005,
        position_pct=0.2
    )
    
    print("回测引擎初始化完成")
    print(f"手续费: {engine.execution_sim.commission}")
    print(f"滑点: {engine.execution_sim.slippage}")
    print(f"仓位比例: {engine.position_sizer.risk_per_trade}")
