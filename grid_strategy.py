#!/usr/bin/env python3
"""
网格交易策略
适合震荡市场，自动低买高卖
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class GridLevel:
    """网格档位"""
    level: int      # 档位编号
    price: float    # 价格
    buy_orders: List[Dict]   # 买单
    sell_orders: List[Dict]  # 卖单


class GridStrategy:
    """
    网格交易策略
    
    原理:
    - 在震荡区间设置若干档位
    - 价格下跌时买入，上涨时卖出
    - 每一档都赚取差价
    
    优点:
    - 震荡市场收益稳定
    - 无需预测方向
    - 自动执行
    
    缺点:
    - 单边行情可能卖飞/套牢
    - 需要足够资金
    """
    
    def __init__(self, 
                 symbol: str = "ETHUSDT",
                 grid_count: int = 10,
                 grid_range: float = 0.10,  # 10%震荡范围
                 order_amount: float = 100,  # 每档订单金额(USDT)
                 upper_price: float = None,
                 lower_price: float = None):
        
        self.symbol = symbol
        self.grid_count = grid_count
        self.grid_range = grid_range
        self.order_amount = order_amount
        self.upper_price = upper_price
        self.lower_price = lower_price
        
        # 状态
        self.grids: List[GridLevel] = []
        self.positions: float = 0  # 持仓数量
        self.total_profit: float = 0  # 总收益(USDT)
        self.trade_count: int = 0
        
        # 配置
        self.grids_file = f"/root/.openclaw/workspace/quant/quant/data/grid_{symbol}.json"
        self.load_state()
    
    def initialize_grids(self, current_price: float):
        """初始化网格"""
        if self.upper_price and self.lower_price:
            price_range = self.upper_price - self.lower_price
        else:
            # 根据当前价格计算范围
            half_range = current_price * self.grid_range / 2
            self.upper_price = current_price * (1 + self.grid_range / 2)
            self.lower_price = current_price * (1 - self.grid_range / 2)
            price_range = self.upper_price - self.lower_price
        
        # 生成网格档位
        step = price_range / self.grid_count
        
        self.grids = []
        for i in range(self.grid_count + 1):
            level = GridLevel(
                level=i,
                price=self.lower_price + step * i,
                buy_orders=[],
                sell_orders=[]
            )
            self.grids.append(level)
        
        print(f"✅ 网格初始化完成: {self.grid_count}档")
        print(f"   价格范围: {self.lower_price:.2f} - {self.upper_price:.2f}")
        print(f"   档位间距: {step:.2f}")
        
        self.save_state()
    
    def generate_signal(self, current_price: float, position: float = 0) -> Dict:
        """
        生成交易信号
        
        Returns:
            {
                'signal': 'BUY'|'SELL'|'HOLD',
                'price': 下单价格,
                'quantity': 数量,
                'reason': 说明
            }
        """
        # 首次初始化
        if not self.grids:
            self.initialize_grids(current_price)
        
        # 找到当前价格所在的档位
        current_level = self._find_level(current_price)
        
        if current_level is None:
            return {'signal': 'HOLD', 'reason': '价格超出网格范围'}
        
        # 检查是否触发买入
        # 价格低于某档位，且该档位没有买单
        for level in self.grids:
            if current_price <= level.price * 0.998:  # 略低于
                if not level.buy_orders:  # 没有买单
                    quantity = self.order_amount / current_price
                    return {
                        'signal': 'BUY',
                        'price': level.price * 0.998,
                        'quantity': quantity,
                        'level': level.level,
                        'reason': f'触发买入档位 {level.level} @ {level.price:.2f}'
                    }
        
        # 检查是否触发卖出
        # 价格高于某档位，且该档位有持仓
        if position > 0:
            for level in self.grids:
                if current_price >= level.price * 1.002:  # 略高于
                    if level.sell_orders:  # 有卖单
                        return {
                            'signal': 'SELL',
                            'price': level.price * 1.002,
                            'quantity': min(position, self.order_amount / level.price),
                            'level': level.level,
                            'reason': f'触发卖出档位 {level.level} @ {level.price:.2f}'
                        }
        
        return {'signal': 'HOLD', 'reason': '无触发条件'}
    
    def _find_level(self, price: float) -> Optional[GridLevel]:
        """找到价格所在的档位"""
        for level in self.grids:
            if price >= level.price:
                return level
        return None
    
    def on_fill(self, order: Dict):
        """
        订单成交回调
        
        Args:
            order: {
                'side': 'BUY'|'SELL',
                'price': 成交价,
                'quantity': 数量,
                'level': 档位
            }
        """
        side = order['side']
        level_idx = order.get('level', 0)
        
        if side == 'BUY':
            # 记录买单成交
            if 0 <= level_idx < len(self.grids):
                self.grids[level_idx].buy_orders.append(order)
                self.positions += order['quantity']
            
            # 在上一档设置卖出
            if level_idx > 0:
                sell_price = self.grids[level_idx - 1].price
                self.grids[level_idx - 1].sell_orders.append({
                    'side': 'SELL',
                    'price': sell_price,
                    'quantity': order['quantity'],
                    'level': level_idx - 1
                })
        
        elif side == 'SELL':
            # 记录卖单成交
            if 0 <= level_idx < len(self.grids):
                self.grids[level_idx].sell_orders.append(order)
                self.positions -= order['quantity']
            
            # 在下一档设置买入
            if level_idx < len(self.grids) - 1:
                buy_price = self.grids[level_idx + 1].price
                self.grids[level_idx + 1].buy_orders.append({
                    'side': 'BUY',
                    'price': buy_price,
                    'quantity': order['quantity'],
                    'level': level_idx + 1
                })
            
            # 计算收益
            profit = order['quantity'] * (order['price'] - self.grids[level_idx].price)
            self.total_profit += profit
        
        self.trade_count += 1
        self.save_state()
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'symbol': self.symbol,
            'grid_count': self.grid_count,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price,
            'positions': self.positions,
            'total_profit': self.total_profit,
            'trade_count': self.trade_count,
            'grids': [
                {
                    'level': g.level,
                    'price': g.price,
                    'has_buy': len(g.buy_orders) > 0,
                    'has_sell': len(g.sell_orders) > 0
                }
                for g in self.grids
            ]
        }
    
    def save_state(self):
        """保存状态"""
        state = {
            'symbol': self.symbol,
            'grids': [
                {
                    'level': g.level,
                    'price': g.price,
                    'buy_orders': g.buy_orders,
                    'sell_orders': g.sell_orders
                }
                for g in self.grids
            ] if self.grids else [],
            'positions': self.positions,
            'total_profit': self.total_profit,
            'trade_count': self.trade_count,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price,
            'updated_at': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(self.grids_file), exist_ok=True)
        
        with open(self.grids_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """加载状态"""
        if os.path.exists(self.grids_file):
            try:
                with open(self.grids_file, 'r') as f:
                    state = json.load(f)
                
                self.positions = state.get('positions', 0)
                self.total_profit = state.get('total_profit', 0)
                self.trade_count = state.get('trade_count', 0)
                self.upper_price = state.get('upper_price')
                self.lower_price = state.get('lower_price')
                
                # 恢复网格
                grids_data = state.get('grids', [])
                self.grids = []
                for g in grids_data:
                    level = GridLevel(
                        level=g['level'],
                        price=g['price'],
                        buy_orders=g.get('buy_orders', []),
                        sell_orders=g.get('sell_orders', [])
                    )
                    self.grids.append(level)
                
                print(f"✅ 状态已恢复: 持仓{self.positions}, 收益{self.total_profit}")
                
            except Exception as e:
                print(f"⚠️ 状态加载失败: {e}")
    
    def reset(self):
        """重置策略"""
        self.grids = []
        self.positions = 0
        self.total_profit = 0
        self.trade_count = 0
        self.save_state()
        print("✅ 策略已重置")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("网格交易策略 - ETH/USDT")
    print("=" * 50)
    
    # 创建策略
    strategy = GridStrategy(
        symbol="ETHUSDT",
        grid_count=10,        # 10档
        grid_range=0.10,      # 10%震荡范围
        order_amount=100      # 每档100U
    )
    
    # 模拟当前价格
    current_price = 2500
    
    # 初始化网格
    strategy.initialize_grids(current_price)
    
    # 生成信号
    signal = strategy.generate_signal(current_price, position=0)
    
    print(f"\n📊 信号:")
    print(f"  {signal}")
    
    # 模拟成交
    if signal['signal'] in ['BUY', 'SELL']:
        order = {
            'side': signal['signal'],
            'price': signal['price'],
            'quantity': signal['quantity'],
            'level': signal.get('level', 0),
            'time': datetime.now().isoformat()
        }
        strategy.on_fill(order)
    
    # 状态
    status = strategy.get_status()
    print(f"\n📈 状态:")
    print(f"  持仓: {status['positions']:.4f} ETH")
    print(f"  收益: {status['total_profit']:.2f} USDT")
    print(f"  交易次数: {status['trade_count']}")
