#!/usr/bin/env python3
"""
智能网格交易策略 v2
基于市场波动率动态调整，支持趋势过滤
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import numpy as np


@dataclass
class MarketState:
    """市场状态"""
    trend: str  # up, down, sideway
    volatility: float  # 波动率
    atr: float  # ATR值
    volume: float  # 成交量


class SmartGridStrategy:
    """
    智能网格策略 v2
    
    优化点:
    1. 动态网格间距 (基于ATR)
    2. 趋势过滤 (避免单边亏损)
    3. 资金管理 (仓/止损)
    4. 盈利保护 (移动止盈)
    5. 自适应仓位
    """
    
    def __init__(self, 
                 symbol: str = "ETHUSDT",
                 base_grid_count: int = 10,
                 grid_range: float = 0.08,  # 8%基础范围
                 order_amount: float = 100,
                 # 新增参数
                 use_trend_filter: bool = True,      # 趋势过滤
                 use_dynamic_grid: bool = True,       # 动态网格
                 use_trailing_stop: bool = True,     # 移动止盈
                 trailing_atr_multiplier: float = 2.0, # 止盈ATR倍数
                 max_position_pct: float = 0.5,     # 最大持仓50%
                 stop_loss_pct: float = 0.05):       # 5%止损
        
        self.symbol = symbol
        self.base_grid_count = base_grid_count
        self.grid_range = grid_range
        self.order_amount = order_amount
        
        # 策略参数
        self.use_trend_filter = use_trend_filter
        self.use_dynamic_grid = use_dynamic_grid
        self.use_trailing_stop = use_trailing_stop
        self.trailing_atr_multiplier = trailing_atr_multiplier
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct
        
        # 状态
        self.grids = []
        self.positions = 0  # 持仓数量
        self.avg_price = 0  # 平均持仓价格
        self.total_profit = 0
        self.trade_count = 0
        
        # 移动止盈
        self.highest_price = 0
        self.trailing_stop_price = 0
        
        # 状态文件
        self.state_file = f"/root/.openclaw/workspace/quant/quant/data/smart_grid_{symbol}.json"
        self.load_state()
    
    def analyze_market(self, prices: List[float], highs: List[float], 
                     lows: List[float], volumes: List[float]) -> MarketState:
        """
        分析市场状态
        """
        # 趋势判断 (简单)
        ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
        ma50 = np.mean(prices[-50:]) if len(prices) >= 50 else prices[-1]
        
        if ma20 > ma50 * 1.02:
            trend = "up"
        elif ma20 < ma50 * 0.98:
            trend = "down"
        else:
            trend = "sideway"
        
        # 波动率
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0.02
        
        # ATR
        trs = []
        for i in range(1, min(14, len(prices))):
            tr = max(highs[-i] - lows[-i], 
                    abs(highs[-i] - prices[-i-1]), 
                    abs(lows[-i] - prices[-i-1]))
            trs.append(tr)
        atr = np.mean(trs) if trs else 20
        
        # 成交量
        volume = np.mean(volumes[-10:]) if volumes else 0
        
        return MarketState(
            trend=trend,
            volatility=volatility,
            atr=atr,
            volume=volume
        )
    
    def initialize_grids(self, current_price: float, market_state: MarketState):
        """
        初始化网格
        根据市场状态动态调整
        """
        # 动态调整网格范围
        if self.use_dynamic_grid:
            # 波动大时扩大范围
            vol_multiplier = 1 + market_state.volatility * 5
            actual_range = min(self.grid_range * vol_multiplier, 0.15)
        else:
            actual_range = self.grid_range
        
        # 网格数量根据趋势调整
        if market_state.trend == "sideway":
            grid_count = self.base_grid_count
        elif market_state.trend == "up":
            grid_count = int(self.base_grid_count * 0.7)  # 减少卖出档位
        else:  # down
            grid_count = int(self.base_grid_count * 0.7)  # 减少买入档位
        
        grid_count = max(grid_count, 5)  # 至少5档
        
        # 计算价格范围
        half_range = current_price * actual_range / 2
        upper = current_price + half_range
        lower = current_price - half_range
        
        # 生成网格
        step = (upper - lower) / grid_count
        
        self.grids = []
        for i in range(grid_count + 1):
            self.grids.append({
                'level': i,
                'price': lower + step * i,
                'buy_triggered': False,
                'sell_triggered': False
            })
        
        self.highest_price = current_price
        
        print(f"✅ 智能网格初始化: {grid_count}档")
        print(f"   趋势: {market_state.trend}, 波动率: {market_state.volatility:.2%}, ATR: {market_state.atr:.2f}")
        print(f"   价格范围: {lower:.2f} - {upper:.2f}")
        
        self.save_state()
    
    def generate_signal(self, 
                       current_price: float,
                       prices: List[float],
                       highs: List[float],
                       lows: List[float],
                       volumes: List[float],
                       positions: float = 0) -> Dict:
        """
        生成交易信号
        
        Args:
            current_price: 当前价格
            prices: 最近100个价格
            highs: 最近高价
            lows: 最近低价
            volumes: 最近成交量
            positions: 当前持仓数量
        """
        # 分析市场状态
        market_state = self.analyze_market(prices, highs, lows, volumes)
        
        # 首次初始化
        if not self.grids:
            self.initialize_grids(current_price, market_state)
        
        # 更新最高价 (用于移动止盈)
        if current_price > self.highest_price:
            self.highest_price = current_price
            # 更新移动止盈价
            if self.use_trailing_stop:
                self.trailing_stop_price = self.highest_price - market_state.atr * self.trailing_atr_multiplier
        
        # 检查是否触发移动止盈
        if self.use_trailing_stop and self.trailing_stop_price > 0:
            if positions > 0 and current_price < self.trailing_stop_price:
                return {
                    'signal': 'SELL',
                    'action': 'trailing_stop',
                    'price': current_price,
                    'quantity': positions,
                    'reason': f'移动止盈触发 {self.trailing_stop_price:.2f}'
                }
        
        # 检查固定止损
        if positions > 0 and self.avg_price > 0:
            loss_pct = (self.avg_price - current_price) / self.avg_price
            if loss_pct >= self.stop_loss_pct:
                return {
                    'signal': 'SELL',
                    'action': 'stop_loss',
                    'price': current_price,
                    'quantity': positions,
                    'reason': f'止损触发 {loss_pct:.1%}'
                }
        
        # 趋势过滤
        if self.use_trend_filter and market_state.trend in ['up', 'down']:
            # 单边上涨: 只买不卖 (除非触发止盈/止损)
            if market_state.trend == 'up' and positions == 0:
                # 下跌到支撑位才买
                support_level = self._find_support_level(prices)
                if current_price <= support_level * 1.01:
                    return self._create_buy_signal(current_price, positions, market_state)
            
            # 单边下跌: 只卖不买
            elif market_state.trend == 'down' and positions > 0:
                # 上涨到压力位才卖
                resistance_level = self._find_resistance_level(prices)
                if current_price >= resistance_level * 0.99:
                    return {
                        'signal': 'SELL',
                        'action': 'trend_exit',
                        'price': current_price,
                        'quantity': positions,
                        'reason': f'单边下跌，平仓离场'
                    }
            
            return {'signal': 'HOLD', 'reason': f'趋势 {market_state.trend}，等待机会'}
        
        # 震荡行情: 正常网格交易
        return self._grid_trading(current_price, positions, market_state)
    
    def _find_support_level(self, prices: List[float]) -> float:
        """找支撑位 (20日低点)"""
        return min(prices[-20:]) if len(prices) >= 20 else prices[-1]
    
    def _find_resistance_level(self, prices: List[float]) -> float:
        """找压力位 (20日高点)"""
        return max(prices[-20:]) if len(prices) >= 20 else prices[-1]
    
    def _grid_trading(self, current_price: float, positions: float, 
                     market_state: MarketState) -> Dict:
        """网格交易逻辑"""
        # 动态调整网格间距 (基于ATR)
        atr = market_state.atr
        
        for grid in self.grids:
            # 买入触发 (价格触及网格线，且未触发过)
            if not grid['buy_triggered']:
                trigger_price = grid['price'] * (1 - atr / current_price * 0.5)
                if current_price <= trigger_price:
                    # 检查是否超过最大持仓
                    max_buy = self.max_position_pct * self.order_amount / current_price * 10
                    
                    if positions < max_buy:
                        grid['buy_triggered'] = True
                        return {
                            'signal': 'BUY',
                            'action': 'grid_buy',
                            'price': current_price,
                            'quantity': self.order_amount / current_price,
                            'level': grid['level'],
                            'reason': f'网格买入 档位{grid["level"]}'
                        }
            
            # 卖出触发
            if not grid['sell_triggered'] and positions > 0:
                trigger_price = grid['price'] * (1 + atr / current_price * 0.5)
                if current_price >= trigger_price:
                    grid['sell_triggered'] = True
                    return {
                        'signal': 'SELL',
                        'action': 'grid_sell',
                        'price': current_price,
                        'quantity': min(positions, self.order_amount / current_price),
                        'level': grid['level'],
                        'reason': f'网格卖出 档位{grid["level"]}'
                    }
        
        return {'signal': 'HOLD', 'reason': '无网格触发'}
    
    def _create_buy_signal(self, current_price, positions, market_state):
        """创建买入信号"""
        max_buy = self.max_position_pct * self.order_amount / current_price * 10
        if positions < max_buy:
            return {
                'signal': 'BUY',
                'action': 'trend_buy',
                'price': current_price,
                'quantity': self.order_amount / current_price,
                'reason': f'趋势逢低买入'
            }
        return {'signal': 'HOLD', 'reason': '仓位已满'}
    
    def on_fill(self, order: Dict):
        """订单成交回调"""
        side = order['side']
        price = order['price']
        quantity = order['quantity']
        
        if side == 'BUY':
            # 更新持仓
            if self.positions > 0:
                self.avg_price = (self.avg_price * self.positions + price * quantity) / (self.positions + quantity)
            else:
                self.avg_price = price
            
            self.positions += quantity
            self.trade_count += 1
        
        elif side == 'SELL':
            # 计算收益
            profit = (price - self.avg_price) * quantity
            self.total_profit += profit
            
            self.positions -= quantity
            self.trade_count += 1
            
            if self.positions <= 0:
                self.positions = 0
                self.avg_price = 0
        
        self.save_state()
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'symbol': self.symbol,
            'positions': self.positions,
            'avg_price': self.avg_price,
            'total_profit': self.total_profit,
            'trade_count': self.trade_count,
            'highest_price': self.highest_price,
            'trailing_stop': self.trailing_stop_price,
            'grid_count': len(self.grids)
        }
    
    def save_state(self):
        """保存状态"""
        state = {
            'symbol': self.symbol,
            'grids': self.grids,
            'positions': self.positions,
            'avg_price': self.avg_price,
            'total_profit': self.total_profit,
            'trade_count': self.trade_count,
            'highest_price': self.highest_price,
            'trailing_stop_price': self.trailing_stop_price,
            'updated_at': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """加载状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.grids = state.get('grids', [])
                self.positions = state.get('positions', 0)
                self.avg_price = state.get('avg_price', 0)
                self.total_profit = state.get('total_profit', 0)
                self.trade_count = state.get('trade_count', 0)
                self.highest_price = state.get('highest_price', 0)
                self.trailing_stop_price = state.get('trailing_stop_price', 0)
                
                print(f"✅ 状态已恢复")
            except Exception as e:
                print(f"⚠️ 状态加载失败: {e}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("智能网格策略 v2 - ETH/USDT")
    print("=" * 50)
    
    # 获取数据
    from binance.client import Client
    from config import API_KEY, SECRET_KEY, TESTNET
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    
    klines = client.get_klines(symbol='ETHUSDT', interval='1h', limit=100)
    
    prices = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    
    current_price = prices[-1]
    
    # 创建策略
    strategy = SmartGridStrategy(
        symbol="ETHUSDT",
        base_grid_count=10,
        grid_range=0.08,
        order_amount=100,
        use_trend_filter=True,
        use_dynamic_grid=True,
        use_trailing_stop=True,
        trailing_atr_multiplier=2.0,
        max_position_pct=0.5,
        stop_loss_pct=0.05
    )
    
    # 生成信号
    signal = strategy.generate_signal(
        current_price=current_price,
        prices=prices,
        highs=highs,
        lows=lows,
        volumes=volumes,
        positions=0
    )
    
    print(f"\n📊 当前价格: {current_price}")
    print(f"\n📈 信号:")
    print(json.dumps(signal, indent=2, ensure_ascii=False))
    
    # 状态
    status = strategy.get_status()
    print(f"\n📉 状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
