#!/usr/bin/env python3
"""
交易成本分析器
精确计算交易成本、滑点影响、最优下单方式
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


class TransactionCostAnalyzer:
    """
    交易成本分析器
    
    功能:
    - 手续费计算
    - 滑点估算
    - 成本优化建议
    - 最优下单策略
    """
    
    # 各市场手续费率
    COMMISSION_RATES = {
        'binance_future': {'maker': 0.0002, 'taker': 0.0007},
        'binance_spot': {'maker': 0.001, 'taker': 0.001},
        'ibkr': {'maker': 0.005, 'taker': 0.005},  #每股
        'a_stock': {'maker': 0.0001, 'taker': 0.0003},  # 万分之一
    }
    
    # 各市场平均滑点 (%)
    SLIPPAGE_RATES = {
        'binance': 0.03,
        'a_stock': 0.05,
        'us_stock': 0.02,
    }
    
    def __init__(self, market: str = 'binance'):
        self.market = market
        self.commission = self.COMMISSION_RATES.get(market, {'maker': 0.001, 'taker': 0.001})
        self.slippage = self.SLIPPAGE_RATES.get(market, 0.05)
    
    def calculate_commission(self, price: float, quantity: float, side: str = 'buy') -> Dict:
        """
        计算手续费
        
        Args:
            price: 价格
            quantity: 数量
            side: buy/sell
        
        Returns:
            手续费详情
        """
        value = price * quantity
        
        if self.market == 'ibkr':
            # IBKR 按每股收费
            commission = quantity * self.commission['taker']
        elif self.market == 'a_stock':
            # A股万分比
            commission = value * self.commission['taker']
        else:
            # 币安等按比例
            commission = value * self.commission['taker']
        
        return {
            'gross_value': value,
            'commission': round(commission, 4),
            'commission_rate': self.commission['taker'],
            'net_value': value - commission if side == 'buy' else value - commission
        }
    
    def calculate_slippage(self, price: float, quantity: float, side: str = 'buy', 
                          volatility: float = 0.02) -> Dict:
        """
        计算滑点
        
        Args:
            price: 价格
            quantity: 数量
            side: buy/sell
            volatility: 波动率
        
        Returns:
            滑点详情
        """
        # 大额订单滑点加成
        value = price * quantity
        size_multiplier = 1.0
        
        if value > 10000:
            size_multiplier = 1.5
        if value > 50000:
            size_multiplier = 2.0
        if value > 100000:
            size_multiplier = 3.0
        
        # 波动率影响
        vol_multiplier = 1 + volatility * 10
        
        # 基础滑点
        slippage_pct = self.slippage * size_multiplier * vol_multiplier
        
        if side == 'buy':
            # 买入时买贵
            slippage_cost = price * quantity * slippage_pct
            execution_price = price * (1 + slippage_pct)
        else:
            # 卖出时卖便宜
            slippage_cost = price * quantity * slippage_pct
            execution_price = price * (1 - slippage_pct)
        
        return {
            'base_slippage_pct': self.slippage,
            'actual_slippage_pct': round(slippage_pct * 100, 4),
            'slippage_cost': round(slippage_cost, 4),
            'execution_price': round(execution_price, 4),
            'size_multiplier': size_multiplier
        }
    
    def calculate_total_cost(self, price: float, quantity: float, side: str = 'buy',
                           volatility: float = 0.02) -> Dict:
        """
        计算总交易成本
        """
        commission = self.calculate_commission(price, quantity, side)
        slippage = self.calculate_slippage(price, quantity, side, volatility)
        
        gross_value = price * quantity
        total_cost = commission['commission'] + slippage['slippage_cost']
        cost_pct = total_cost / gross_value * 100
        
        return {
            'market': self.market,
            'side': side,
            'quantity': quantity,
            'limit_price': price,
            'gross_value': gross_value,
            'commission': commission['commission'],
            'slippage': slippage['slippage_cost'],
            'total_cost': round(total_cost, 4),
            'cost_pct': round(cost_pct, 4),
            'net_value': gross_value + total_cost if side == 'buy' else gross_value - total_cost,
            'execution_price': slippage['execution_price']
        }
    
    def optimize_order_size(self, target_value: float, max_cost_pct: float = 0.1) -> Dict:
        """
        优化下单规模
        
        找出满足最大成本限制的最大下单量
        """
        # 二分查找最优
        low, high = 0, target_value
        best_size = 0
        
        for _ in range(50):
            mid = (low + high) / 2
            quantity = mid / 100000  # 假设价格100
            
            cost = self.calculate_total_cost(100, quantity, 'buy')
            
            if cost['cost_pct'] <= max_cost_pct:
                best_size = mid
                low = mid
            else:
                high = mid
        
        return {
            'target_value': target_value,
            'max_cost_pct': max_cost_pct,
            'optimal_value': round(best_size, 2),
            'recommended_split': max(1, int(target_value / best_size))
        }
    
    def compare_markets(self, price: float, quantity: float) -> pd.DataFrame:
        """
        比较各市场成本
        """
        markets = ['binance_future', 'binance_spot', 'a_stock', 'ibkr']
        results = []
        
        for market in markets:
            analyzer = TransactionCostAnalyzer(market)
            cost = analyzer.calculate_total_cost(price, quantity, 'buy')
            
            results.append({
                'market': market,
                'total_cost': cost['total_cost'],
                'cost_pct': cost['cost_pct']
            })
        
        return pd.DataFrame(results).sort_values('cost_pct')


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("交易成本分析器")
    print("=" * 50)
    
    # 创建分析器
    analyzer = TransactionCostAnalyzer('binance_future')
    
    # 计算成本
    cost = analyzer.calculate_total_cost(50000, 0.5, 'buy', volatility=0.03)
    
    print("\n📊 交易成本明细:")
    for k, v in cost.items():
        print(f"  {k}: {v}")
    
    # 优化下单
    opt = analyzer.optimize_order_size(50000, max_cost_pct=0.1)
    print(f"\n📈 最优下单建议:")
    print(f"  目标金额: ${opt['target_value']}")
    print(f"  最优金额: ${opt['optimal_value']}")
    print(f"  建议分单: {opt['recommended_split']} 次")
    
    # 市场比较
    print("\n🌍 市场成本比较:")
    df = analyzer.compare_markets(50000, 1)
    print(df)
