"""
投资组合管理模块
多标的/多策略组合管理
"""

from datetime import datetime
from typing import Dict, List, Optional
import json
import numpy as np


class Portfolio:
    """
    投资组合
    
    管理多个账户/策略
    """
    
    def __init__(self, name: str = "portfolio"):
        self.name = name
        self.accounts = {}  # {account_id: Account}
        self.strategies = {}  # {strategy_name: weight}
        self.positions = {}  # 汇总持仓
        self.total_value = 0
        self.timestamp = datetime.now()
    
    def add_account(self, account_id: str, account, weight: float = 1.0):
        """添加账户"""
        self.accounts[account_id] = account
        self.strategies[account_id] = weight
    
    def remove_account(self, account_id: str):
        """移除账户"""
        if account_id in self.accounts:
            del self.accounts[account_id]
            del self.strategies[account_id]
    
    def update(self):
        """更新组合状态"""
        self.total_value = 0
        self.positions = {}
        
        for account_id, account in self.accounts.items():
            # 更新账户
            account.update({})
            
            # 汇总
            self.total_value += account.total_value
            
            # 汇总持仓
            for symbol, pos in account.positions.items():
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'volume': 0,
                        'value': 0,
                        'weight': 0
                    }
                self.positions[symbol]['volume'] += pos.volume
                self.positions[symbol]['value'] += pos.value
        
        # 计算权重
        for symbol in self.positions:
            if self.total_value > 0:
                self.positions[symbol]['weight'] = (
                    self.positions[symbol]['value'] / self.total_value
                )
        
        self.timestamp = datetime.now()
    
    def get_position_summary(self) -> List[Dict]:
        """获取持仓汇总"""
        summary = []
        for symbol, pos in self.positions.items():
            summary.append({
                'symbol': symbol,
                'volume': round(pos['volume'], 4),
                'value': round(pos['value'], 2),
                'weight': round(pos['weight'] * 100, 2)
            })
        return sorted(summary, key=lambda x: x['weight'], reverse=True)
    
    def rebalance(self, target_weights: Dict[str, float]):
        """
        组合再平衡
        
        Args:
            target_weights: 目标权重 {symbol: weight}
        """
        self.update()
        
        # 需要调整的仓位
        for symbol, target_weight in target_weights.items():
            current_weight = self.positions.get(symbol, {}).get('weight', 0)
            diff = target_weight - current_weight
            
            # 需要买入/卖出
            if diff > 0.01:  # 买入
                print(f"需要买入 {symbol}: {diff*100:.1f}%")
            elif diff < -0.01:  # 卖出
                print(f"需要卖出 {symbol}: {abs(diff)*100:.1f}%")
    
    def get_metrics(self) -> Dict:
        """获取组合指标"""
        self.update()
        
        returns = []
        for account in self.accounts.values():
            if hasattr(account, 'returns'):
                returns.extend(account.returns)
        
        if returns:
            avg_return = np.mean(returns)
            volatility = np.std(returns)
            sharpe = avg_return / volatility * np.sqrt(252) if volatility > 0 else 0
        else:
            avg_return = 0
            volatility = 0
            sharpe = 0
        
        return {
            'total_value': round(self.total_value, 2),
            'positions': len(self.positions),
            'accounts': len(self.accounts),
            'avg_return': round(avg_return * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe, 2)
        }
    
    def to_dict(self) -> Dict:
        """序列化"""
        self.update()
        return {
            'name': self.name,
            'total_value': round(self.total_value, 2),
            'positions': self.get_position_summary(),
            'metrics': self.get_metrics(),
            'timestamp': self.timestamp.isoformat()
        }


class StrategyPortfolio:
    """
    策略组合
    
    多策略组合管理
    """
    
    def __init__(self, name: str = "strategy_portfolio"):
        self.name = name
        self.strategies = {}  # {name: {'func': strategy_func, 'weight': w, 'enabled': True}}
        self.signals = {}  # 各策略信号
        self.equity_curves = {}  # 各策略权益
        self.weights = {}  # 动态权重
    
    def add_strategy(self, name: str, strategy_func, weight: float = 1.0):
        """添加策略"""
        self.strategies[name] = {
            'func': strategy_func,
            'weight': weight,
            'enabled': True
        }
        self.equity_curves[name] = []
    
    def remove_strategy(self, name: str):
        """移除策略"""
        if name in self.strategies:
            del self.strategies[name]
            del self.equity_curves[name]
    
    def generate_signals(self, data: Dict) -> Dict:
        """
        生成汇总信号
        
        Args:
            data: 市场数据
        
        Returns:
            Dict: {symbol: {'action': 'BUY'/'SELL'/'HOLD', 'weight': 总权重, 'signals': 各策略信号}}
        """
        self.signals = {}
        
        # 各策略分别产生信号
        for name, config in self.strategies.items():
            if not config['enabled']:
                continue
            
            try:
                signal = config['func'](data)
                self.signals[name] = {
                    'signal': signal,
                    'weight': config['weight']
                }
            except Exception as e:
                print(f"策略 {name} 执行错误: {e}")
        
        # 汇总信号
        combined = {}
        for name, sig_data in self.signals.items():
            signal = sig_data.get('signal')
            if not signal or signal == 'HOLD':
                continue
            
            if signal not in combined:
                combined[signal] = {
                    'weight': 0,
                    'strategies': []
                }
            
            combined[signal]['weight'] += sig_data['weight']
            combined[signal]['strategies'].append(name)
        
        return combined
    
    def get_best_signal(self, data: Dict) -> str:
        """获取最优信号"""
        signals = self.generate_signals(data)
        
        if not signals:
            return 'HOLD'
        
        # 选择权重最高的
        best = max(signals.items(), key=lambda x: x[1]['weight'])
        return best[0]
    
    def update_equity(self, name: str, equity: float):
        """更新策略权益"""
        if name in self.equity_curves:
            self.equity_curves[name].append(equity)
    
    def get_performance(self) -> Dict:
        """获取各策略表现"""
        performance = {}
        
        for name, curve in self.equity_curves.items():
            if len(curve) < 2:
                performance[name] = {'return': 0, 'enabled': True}
                continue
            
            ret = (curve[-1] - curve[0]) / curve[0]
            performance[name] = {
                'return': round(ret * 100, 2),
                'enabled': self.strategies[name]['enabled'],
                'weight': self.strategies[name]['weight']
            }
        
        return performance


# 全局组合实例
_portfolio: Optional[Portfolio] = None


def get_portfolio(name: str = "default") -> Portfolio:
    """获取组合实例"""
    global _portfolio
    if _portfolio is None:
        _portfolio = Portfolio(name)
    return _portfolio


if __name__ == '__main__':
    # 测试
    from account import Account
    
    portfolio = get_portfolio()
    
    # 添加账户
    acc1 = Account("acc1", 100000)
    acc2 = Account("acc2", 100000)
    
    portfolio.add_account("acc1", acc1, 0.6)
    portfolio.add_account("acc2", acc2, 0.4)
    
    portfolio.update()
    
    print(portfolio.get_metrics())
