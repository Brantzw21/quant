#!/usr/bin/env python3
"""
投资组合再平衡器
定期调整资产权重
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import json
from typing import Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class TargetAllocation:
    """目标配置"""
    symbol: str
    target_weight: float  # 目标权重 0-1
    min_weight: float = 0  # 最小权重
    max_weight: float = 1  # 最大权重


@dataclass
class RebalanceResult:
    """再平衡结果"""
    timestamp: str
    trades: List[Dict]
    before_weights: Dict[str, float]
    after_weights: Dict[str, float]
    rebalance_cost: float  # 交易成本
    triggered: bool
    reason: str


class Rebalancer:
    """
    投资组合再平衡器
    
    策略:
    - 阈值再平衡 (偏离阈值触发)
    - 定期再平衡 (固定周期)
    - 动态再平衡 (基于波动率)
    """
    
    def __init__(self, 
                 targets: List[TargetAllocation],
                 threshold: float = 0.05,  # 偏离阈值 5%
                 max_rebalance: float = 0.2):  # 每次最大调整 20%
        self.targets = {t.symbol: t for t in targets}
        self.threshold = threshold
        self.max_rebalance = max_rebalance
        
        # 记录
        self.history: List[RebalanceResult] = []
        
        # 读取当前配置
        self.weights_file = "/root/.openclaw/workspace/quant/quant/data/rebalance_weights.json"
    
    def get_current_weights(self, portfolio_value: float) -> Dict[str, float]:
        """获取当前权重"""
        # 从文件读取
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file, 'r') as f:
                    data = json.load(f)
                    return data.get('weights', {})
            except:
                pass
        
        # 默认等权
        n = len(self.targets)
        return {symbol: 1/n for symbol in self.targets}
    
    def set_current_weights(self, weights: Dict[str, float]):
        """保存当前权重"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'weights': weights
        }
        
        os.makedirs(os.path.dirname(self.weights_file), exist_ok=True)
        
        with open(self.weights_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def check_rebalance_needed(self, current_weights: Dict[str, float]) -> bool:
        """检查是否需要再平衡"""
        for symbol, target in self.targets.items():
            current = current_weights.get(symbol, 0)
            deviation = abs(current - target.target_weight)
            
            if deviation > self.threshold:
                return True
        
        return False
    
    def calculate_trades(self, 
                       current_weights: Dict[str, float],
                       portfolio_value: float) -> List[Dict]:
        """
        计算需要执行的交易
        """
        trades = []
        
        # 按偏离大小排序
        deviations = []
        
        for symbol, target in self.targets.items():
            current = current_weights.get(symbol, 0)
            deviation = target.target_weight - current
            deviations.append((symbol, deviation, current, target.target_weight))
        
        # 按偏离绝对值排序
        deviations.sort(key=lambda x: abs(x[1]), reverse=True)
        
        total_rebalance = 0
        
        for symbol, deviation, current, target in deviations:
            # 计算调整金额
            adjust_value = deviation * portfolio_value
            
            # 限制每次调整
            max_adjust = portfolio_value * self.max_rebalance
            
            if abs(adjust_value) > max_adjust:
                adjust_value = max_adjust if adjust_value > 0 else -max_adjust
            
            if abs(adjust_value) > 10:  # 至少10U
                # 假设价格 (简化)
                price = 50000 if 'BTC' in symbol else 3000
                quantity = adjust_value / price
                
                trades.append({
                    'symbol': symbol,
                    'side': 'BUY' if adjust_value > 0 else 'SELL',
                    'value': abs(adjust_value),
                    'quantity': quantity,
                    'current_weight': current,
                    'target_weight': target,
                    'adjust': adjust_value
                })
                
                total_rebalance += abs(adjust_value)
                
                # 检查是否达到最大调整
                if total_rebalance >= portfolio_value * self.max_rebalance:
                    break
        
        return trades
    
    def rebalance(self, portfolio_value: float, reason: str = "threshold") -> RebalanceResult:
        """
        执行再平衡
        """
        # 获取当前权重
        current_weights = self.get_current_weights(portfolio_value)
        
        # 检查是否需要
        if not self.check_rebalance_needed(current_weights):
            return RebalanceResult(
                timestamp=datetime.now().isoformat(),
                trades=[],
                before_weights=current_weights,
                after_weights=current_weights,
                rebalance_cost=0,
                triggered=False,
                reason="No rebalance needed"
            )
        
        # 计算交易
        trades = self.calculate_trades(current_weights, portfolio_value)
        
        # 计算交易成本 (假设0.1%)
        total_value = sum(t['value'] for t in trades)
        cost = total_value * 0.001
        
        # 更新权重
        after_weights = {}
        
        for symbol in self.targets:
            current = current_weights.get(symbol, 0)
            trade_value = next((t['value'] for t in trades if t['symbol'] == symbol), 0)
            side = next((t['side'] for t in trades if t['symbol'] == symbol), None)
            
            if side == 'BUY':
                after_weights[symbol] = current + trade_value / portfolio_value
            elif side == 'SELL':
                after_weights[symbol] = current - trade_value / portfolio_value
            else:
                after_weights[symbol] = current
        
        # 保存
        self.set_current_weights(after_weights)
        
        # 记录
        result = RebalanceResult(
            timestamp=datetime.now().isoformat(),
            trades=trades,
            before_weights=current_weights,
            after_weights=after_weights,
            rebalance_cost=cost,
            triggered=True,
            reason=reason
        )
        
        self.history.append(result)
        
        return result
    
    def scheduled_rebalance(self, portfolio_value: float) -> RebalanceResult:
        """定时再平衡"""
        return self.rebalance(portfolio_value, reason="scheduled")
    
    def get_report(self) -> Dict:
        """获取再平衡报告"""
        if not self.history:
            return {'message': 'No rebalancing history'}
        
        latest = self.history[-1]
        
        return {
            'last_rebalance': latest.timestamp,
            'triggered': latest.triggered,
            'trades_count': len(latest.trades),
            'total_cost': latest.rebalance_cost,
            'before_weights': latest.before_weights,
            'after_weights': latest.after_weights,
            'total_rebalances': len(self.history)
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("投资组合再平衡器")
    print("=" * 50)
    
    # 设置目标配置
    targets = [
        TargetAllocation("BTC", 0.5, 0.3, 0.7),
        TargetAllocation("ETH", 0.3, 0.15, 0.5),
        TargetAllocation("SPY", 0.2, 0.1, 0.3),
    ]
    
    # 创建再平衡器
    rebalancer = Rebalancer(targets, threshold=0.05)
    
    # 当前组合价值
    portfolio_value = 100000
    
    # 模拟当前权重 (偏离目标)
    current_weights = {
        'BTC': 0.6,   # 偏离 +0.1
        'ETH': 0.2,   # 偏离 -0.1
        'SPY': 0.2    # 刚好
    }
    
    # 保存当前权重
    rebalancer.set_current_weights(current_weights)
    
    # 执行再平衡
    print("\n📊 执行再平衡...")
    result = rebalancer.rebalance(portfolio_value)
    
    print(f"触发: {result.triggered}")
    print(f"原因: {result.reason}")
    
    print(f"\n📈 交易:")
    for t in result.trades:
        print(f"  {t['side']} {t['symbol']}: ${t['value']:.2f}")
    
    print(f"\n💰 交易成本: ${result.rebalance_cost:.2f}")
    
    print(f"\n⚖️ 权重变化:")
    for symbol in result.before_weights:
        before = result.before_weights[symbol]
        after = result.after_weights[symbol]
        print(f"  {symbol}: {before:.1%} -> {after:.1%}")
    
    # 报告
    print("\n📋 再平衡报告:")
    print(rebalancer.get_report())
