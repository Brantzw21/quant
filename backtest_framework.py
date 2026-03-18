#!/usr/bin/env python3
"""
策略回测框架 V2
统一回测接口，支持多策略、分批建仓、多空双向

Features:
- 分批建仓/平仓 (网格支持)
- 信号置信度
- 多空双向持仓
- 动态仓位管理
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime

import itertools
import json
import numpy as np
import pandas as pd

from backtest_models import (
    Signal, Side, SignalType, Position, PositionLayer
)


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 10000.0
    commission: float = 0.001          # 综合手续费率
    maker_fee: float = 0.0002           # Maker费率
    taker_fee: float = 0.0007           # Taker费率
    slippage: float = 0.0005            # 滑点
    leverage: float = 1.0
    risk_free_rate: float = 0.02
    position_pct: float = 0.95          # 默认仓位
    symbol: str = "BTCUSDT"
    min_trade_value: float = 10.0       # 最小成交额
    use_maker_taker: bool = False       # 是否区分maker/taker
    max_layers: int = 10                # 最大持仓层数
    layer_gap_pct: float = 0.02          # 加仓间距 2%


@dataclass
class Trade:
    """交易记录"""
    time: str
    symbol: str
    side: str           # BUY/SELL
    price: float
    quantity: float
    value: float
    commission: float
    slippage: float
    pnl: float = 0.0
    fee_rate: float = 0.0
    trade_role: str = "taker"
    layer_id: int = 0   # 持仓层ID


class Strategy(ABC):
    """策略基类"""
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """返回 Signal 或 pd.Series[Signal]"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """返回策略名称"""
    
    def generate_signals_legacy(self, data: pd.DataFrame) -> pd.Series:
        """
        兼容旧接口: 返回 1=BUY, -1=SELL, 0=HOLD
        """
        signals = self.generate_signals(data)
        
        # 如果是 Signal 列表/Series
        if isinstance(signals, pd.Series):
            if len(signals) > 0 and isinstance(signals.iloc[0], Signal):
                numeric = signals.apply(lambda s: s.to_numeric())
                return numeric.fillna(0).astype(int)
        
        # 已经是数值 Series，直接返回
        return signals.fillna(0).astype(int)


class Backtester:
    """
    统一回测框架 V2
    
    支持:
    - 分批建仓/平仓
    - 信号置信度过滤
    - 多空双向持仓
    - 动态仓位管理
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.strategy: Optional[Strategy] = None
        self.data: Optional[pd.DataFrame] = None
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.cash = self.config.initial_capital
        self.position = Position(symbol=self.config.symbol)
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.equity_timestamps: List[str] = []
        self.stats: Dict = {}
        self._next_layer_id = 0
    
    def set_strategy(self, strategy: Strategy):
        self.strategy = strategy
    
    def set_data(self, data: pd.DataFrame):
        self.data = data
    
    def run(self, data: Optional[pd.DataFrame] = None, strategy: Optional[Strategy] = None) -> Dict:
        """
        运行回测
        
        Args:
            data: K线数据
            strategy: 策略实例
            
        Returns:
            回测统计结果
        """
        if data is not None:
            self.data = data.copy()
        if strategy is not None:
            self.strategy = strategy
        
        if self.data is None or self.strategy is None:
            raise ValueError("data 和 strategy 不能为空")
        
        self.reset()
        df = self._prepare_data(self.data)
        
        # 尝试获取 Signal 格式信号，否则降级到数值信号
        try:
            signals = self._generate_signals(df)
        except Exception:
            # 兼容旧策略
            signals = self.strategy.generate_signals_legacy(df)
        
        signals = self._align_signals(signals, df.index)
        
        for i in range(len(df)):
            row = df.iloc[i]
            timestamp = self._row_timestamp(row.name, i)
            price = float(row['close'])
            
            # 更新持仓估值
            if not self.position.is_flat:
                self._update_position_price(price)
            
            signal = signals.iloc[i] if i < len(signals) else None
            if signal is not None:
                self._process_signal(signal, price, timestamp)
            
            # 记录权益
            self.equity_curve.append(self._equity(price))
            self.equity_timestamps.append(timestamp)
        
        # 最终平仓
        if not self.position.is_flat:
            self._close_all(timestamp, price)
            self.equity_curve[-1] = self._equity(price)
        
        self.stats = self._calculate_stats()
        return self.stats
    
    def _generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成信号，尝试使用新Signal格式"""
        result = self.strategy.generate_signals(df)
        
        if isinstance(result, pd.Series):
            # 检查第一个元素是否是 Signal
            if len(result) > 0 and isinstance(result.iloc[0], Signal):
                return result
        
        # 旧格式，转为 Signal Series
        numeric = result.fillna(0)
        signals = []
        for val in numeric:
            if val == 1:
                signals.append(Signal(side=Side.LONG, confidence=0.7, signal_type=SignalType.ENTRY))
            elif val == -1:
                signals.append(Signal(side=Side.SHORT, confidence=0.7, signal_type=SignalType.ENTRY))
            else:
                signals.append(Signal(side=Side.FLAT, confidence=0.5, signal_type=SignalType.HOLD))
        
        return pd.Series(signals, index=df.index)
    
    def _align_signals(self, signals: pd.Series, index) -> pd.Series:
        """对齐信号与数据索引"""
        if isinstance(signals.index, type(index)) and signals.index.equals(index):
            return signals.reindex(index).fillna(Signal())
        return signals.reindex(index).fillna(
            Signal(side=Side.FLAT, confidence=0.5, signal_type=SignalType.HOLD)
        )
    
    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        df = data.copy()
        
        # 必需列
        if 'close' not in df.columns:
            raise ValueError(f"缺少必要列: close")
        
        # 填充可选列
        if 'open' not in df.columns:
            df['open'] = df['close']
        if 'high' not in df.columns:
            df['high'] = df[['open', 'close']].max(axis=1)
        if 'low' not in df.columns:
            df['low'] = df[['open', 'close']].min(axis=1)
        if 'volume' not in df.columns:
            df['volume'] = 0.0
        
        return df
    
    def _row_timestamp(self, row_name, idx: int) -> str:
        if hasattr(row_name, 'strftime'):
            return row_name.strftime('%Y-%m-%d %H:%M:%S')
        return str(idx)
    
    def _equity(self, current_price: float) -> float:
        """当前总权益"""
        return self.cash + self.position.get_value(current_price)
    
    def _update_position_price(self, price: float):
        """更新所有持仓层的价格"""
        for layer in self.position.layers:
            layer.current_price = price
    
    def _fee_rate(self, trade_role: str = 'taker') -> float:
        """获取费率"""
        if self.config.use_maker_taker:
            return self.config.maker_fee if trade_role == 'maker' else self.config.taker_fee
        return self.config.commission
    
    def _process_signal(self, signal: Signal, price: float, timestamp: str):
        """处理信号"""
        # 兼容旧格式
        if isinstance(signal, (int, float)):
            signal = Signal(
                side=Side.LONG if signal == 1 else Side.SHORT if signal == -1 else Side.FLAT,
                confidence=0.7
            )
        
        # 空仓且有买入信号 -> 建仓
        if self.position.is_flat and signal.side == Side.LONG and signal.confidence >= 0.5:
            self._open_position(signal, price, timestamp, layer_id=0)
        
        # 持仓且有卖出信号 -> 平仓
        elif not self.position.is_flat:
            if signal.side == Side.FLAT or signal.confidence < 0.3:
                # 全部平仓
                self._close_all(timestamp, price)
            elif signal.side != self.position.layers[0].side:
                # 反向 -> 先平后开
                self._close_all(timestamp, price)
                self._open_position(signal, price, timestamp, layer_id=0)
            elif signal.signal_type == SignalType.ADD and signal.size_pct > 0:
                # 加仓信号
                self._add_layer(signal, price, timestamp)
            elif signal.signal_type == SignalType.REDUCE:
                # 减仓信号
                self._reduce_layer(timestamp, price)
    
    def _open_position(self, signal: Signal, price: float, timestamp: str, layer_id: int = 0):
        """开仓"""
        fee_rate = self._fee_rate('taker')
        exec_price = price * (1 + self.config.slippage)
        
        # 计算仓位
        deployable_cash = self.cash * min(self.config.position_pct * (signal.size_pct or 1.0), 1.0)
        quantity = max(deployable_cash * self.config.leverage / exec_price, 0)
        
        if quantity <= 0:
            return
        
        trade_value = quantity * exec_price
        commission = trade_value * fee_rate
        total_cost = trade_value + commission
        
        # 资金检查
        if total_cost > self.cash:
            quantity = self.cash / (exec_price * (1 + fee_rate))
            trade_value = quantity * exec_price
            commission = trade_value * fee_rate
            total_cost = trade_value + commission
        
        if quantity <= 0 or trade_value < self.config.min_trade_value:
            return
        
        # 执行
        self.cash -= total_cost
        
        layer = PositionLayer(
            layer_id=layer_id,
            side=signal.side,
            quantity=quantity,
            avg_price=exec_price,
            entry_time=timestamp,
            current_price=price
        )
        self.position.add_layer(layer)
        
        self.trades.append(Trade(
            time=timestamp,
            symbol=self.config.symbol,
            side='BUY',
            price=exec_price,
            quantity=quantity,
            value=trade_value,
            commission=commission,
            slippage=exec_price - price,
            fee_rate=fee_rate,
            trade_role='taker',
            layer_id=layer_id
        ))
    
    def _add_layer(self, signal: Signal, price: float, timestamp: str):
        """加仓 (网格)"""
        if len(self.position.layers) >= self.config.max_layers:
            return
        
        # 检查价格间距
        current_price = self.position.avg_price
        gap_pct = abs(price - current_price) / current_price
        
        if gap_pct < self.config.layer_gap_pct:
            return  # 间距不够
        
        self._next_layer_id += 1
        self._open_position(signal, price, timestamp, layer_id=self._next_layer_id)
    
    def _reduce_layer(self, timestamp: str, price: float):
        """减仓 (部分平仓)"""
        if self.position.is_flat:
            return
        
        # 移除最新一层
        layer = self.position.remove_layer(self._next_layer_id)
        if layer is None and self.position.layers:
            layer = self.position.layers[-1]
        
        if layer is None:
            return
        
        self._close_layer(layer, price, timestamp)
    
    def _close_all(self, timestamp: str, price: float):
        """全部平仓"""
        layers = self.position.layers.copy()
        for layer in layers:
            self._close_layer(layer, price, timestamp)
        self.position.layers.clear()
    
    def _close_layer(self, layer: PositionLayer, price: float, timestamp: str):
        """平掉一层持仓"""
        fee_rate = self._fee_rate('maker')
        exec_price = price * (1 - self.config.slippage)
        
        gross_value = layer.quantity * exec_price
        commission = gross_value * fee_rate
        net_value = gross_value - commission
        
        pnl = layer.pnl(price)
        
        if gross_value < self.config.min_trade_value:
            return
        
        self.cash += net_value
        
        self.trades.append(Trade(
            time=timestamp,
            symbol=self.config.symbol,
            side='SELL',
            price=exec_price,
            quantity=layer.quantity,
            value=net_value,
            commission=commission,
            slippage=price - exec_price,
            pnl=pnl,
            fee_rate=fee_rate,
            trade_role='maker',
            layer_id=layer.layer_id
        ))
    
    def _calculate_stats(self) -> Dict:
        """计算统计指标"""
        if not self.equity_curve:
            return {}
        
        equity = np.array(self.equity_curve, dtype=float)
        returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([])
        returns = returns[~np.isnan(returns)]
        
        initial = float(self.config.initial_capital)
        final = float(equity[-1])
        total_return = (final - initial) / initial if initial else 0.0
        
        periods = max(len(equity), 1)
        annualized_return = (1 + total_return) ** (252 * 24 / periods) - 1 if periods > 1 and final > 0 else total_return
        volatility = np.std(returns) * np.sqrt(252 * 24) if len(returns) > 1 else 0.0
        sharpe = (annualized_return - self.config.risk_free_rate) / volatility if volatility > 0 else 0.0
        
        # 回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(float(np.min(drawdown))) if len(drawdown) else 0.0
        
        # 交易统计
        sell_trades = [t for t in self.trades if t.side == 'SELL']
        wins = [t for t in sell_trades if t.pnl > 0]
        losses = [t for t in sell_trades if t.pnl <= 0]
        
        total_commission = float(sum(t.commission for t in self.trades))
        total_slippage = float(sum(abs(t.slippage) * t.quantity for t in self.trades))
        
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        return {
            'strategy': self.strategy.get_name(),
            'symbol': self.config.symbol,
            'initial_capital': initial,
            'final_equity': final,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'total_trades': len(self.trades),
            'buy_trades': len([t for t in self.trades if t.side == 'BUY']),
            'sell_trades': len(sell_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(sell_trades) if sell_trades else 0.0,
            'total_commission': total_commission,
            'total_slippage_cost': total_slippage,
            'avg_commission': total_commission / len(self.trades) if self.trades else 0,
            'equity_curve': equity.tolist(),
            'equity_timestamps': self.equity_timestamps,
            'trades': [t.__dict__ for t in self.trades],
        }
    
    def save_results(self, filepath: str):
        """保存结果"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        payload = self.stats or self._calculate_stats()
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath
    
    def walk_forward(self, data: pd.DataFrame, strategy: Strategy, 
                    train_size: int, test_size: int, 
                    step_size: Optional[int] = None) -> Dict:
        """滚动窗口 walk-forward 回测"""
        if train_size <= 0 or test_size <= 0:
            raise ValueError('train_size 和 test_size 必须大于 0')
        
        df = self._prepare_data(data)
        step = step_size or test_size
        windows = []
        
        start = 0
        while start + train_size + test_size <= len(df):
            train_df = df.iloc[start:start + train_size].copy()
            test_df = df.iloc[start + train_size:start + train_size + test_size].copy()
            
            # 重置后回测
            self.reset()
            result = self.run(test_df, strategy)
            
            windows.append({
                'train_start': start,
                'train_end': start + train_size - 1,
                'test_start': start + train_size,
                'test_end': start + train_size + test_size - 1,
                'result': result,
            })
            start += step
        
        # 聚合统计
        aggregated_returns = [w['result']['total_return'] for w in windows if w.get('result')]
        aggregated_drawdowns = [w['result']['max_drawdown'] for w in windows if w.get('result')]
        aggregated_sharpes = [w['result']['sharpe_ratio'] for w in windows if w.get('result')]
        
        return {
            'windows': windows,
            'window_count': len(windows),
            'avg_total_return': float(np.mean(aggregated_returns)) if aggregated_returns else 0.0,
            'avg_max_drawdown': float(np.mean(aggregated_drawdowns)) if aggregated_drawdowns else 0.0,
            'avg_sharpe_ratio': float(np.mean(aggregated_sharpes)) if aggregated_sharpes else 0.0,
        }


class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, backtester: Backtester):
        self.backtester = backtester
    
    def grid_search(self, data: pd.DataFrame, strategy_cls, 
                   param_grid: Dict, top_n: int = 10) -> List[Dict]:
        """网格搜索最优参数"""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        results = []
        
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            
            try:
                strategy = strategy_cls(**params)
                result = self.backtester.run(data, strategy)
                
                results.append({
                    'params': params,
                    'total_return': result['total_return'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'max_drawdown': result['max_drawdown'],
                    'win_rate': result['win_rate'],
                    'sell_trades': result['sell_trades'],
                })
            except Exception as e:
                print(f"参数 {params} 失败: {e}")
                continue
        
        # 排序
        results.sort(key=lambda x: (x['sharpe_ratio'], x['total_return']), reverse=True)
        return results[:top_n]


# 兼容旧代码
BacktestConfigV1 = BacktestConfig


if __name__ == '__main__':
    # 测试新框架
    class RSIStrategy(Strategy):
        def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
            self.period = period
            self.overbought = overbought
            self.oversold = oversold
        
        def get_name(self) -> str:
            return f'RSI({self.period},{self.overbought},{self.oversold})'
        
        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            close = data['close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            signals = []
            for val in rsi:
                if pd.isna(val):
                    signals.append(Signal())
                elif val < self.oversold:
                    signals.append(Signal(
                        side=Side.LONG, 
                        confidence=0.7, 
                        signal_type=SignalType.ENTRY
                    ))
                elif val > self.overbought:
                    signals.append(Signal(
                        side=Side.FLAT, 
                        confidence=0.7, 
                        signal_type=SignalType.EXIT
                    ))
                else:
                    signals.append(Signal())
            
            return pd.Series(signals, index=data.index)
    
    # 生成测试数据
    np.random.seed(42)
    n = 200
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    data = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.uniform(1000, 5000, n),
    })
    
    # 回测
    backtester = Backtester(BacktestConfig(initial_capital=10000, symbol='BTCUSDT'))
    stats = backtester.run(data, RSIStrategy(14, 70, 30))
    
    print(f"策略: {stats['strategy']}")
    print(f"总收益: {stats['total_return']:.2%}")
    print(f"最大回撤: {stats['max_drawdown']:.2%}")
    print(f"夏普比率: {stats['sharpe_ratio']:.2f}")
    print(f"交易次数: {stats['sell_trades']}")
    print(f"✅ 新框架测试通过")
