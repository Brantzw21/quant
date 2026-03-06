"""
风控模块
包含仓位管理、止损止盈、风险预算等功能
"""

from enum import Enum
from typing import Dict, Any, Optional
import numpy as np


class PositionSizingMethod(Enum):
    """仓位计算方法"""
    FIXED = "fixed"                      # 固定仓位
    KELLY = "kelly"                      # Kelly公式
    VOLATILITY = "volatility"           # 波动率调整
    RISK_PARITY = "risk_parity"          # 风险平价
    EQUAL_WEIGHT = "equal_weight"         # 等权


class RiskManager:
    """
    风险管理器
    负责仓位计算、止损止盈、风险控制
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 止损止盈配置
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.05)      # 止损5%
        self.take_profit_pct = self.config.get('take_profit_pct', 0.15)   # 止盈15%
        self.trailing_stop = self.config.get('trailing_stop', 0.03)     # 追踪止损3%
        
        # 仓位配置
        self.max_position_pct = self.config.get('max_position_pct', 0.95)  # 最大持仓95%
        self.max_loss_per_trade_pct = self.config.get('max_loss_per_trade_pct', 0.02)  # 单笔最大亏损2%
        
        # 风险预算
        self.max_daily_loss_pct = self.config.get('max_daily_loss_pct', 0.05)  # 日内最大亏损5%
        self.max_drawdown_pct = self.config.get('max_drawdown_pct', 0.20)  # 最大回撤20%
        
        # 当前状态
        self.peak_equity = 0
        self.current_drawdown = 0
    
    def calculate_position_size(self, 
                               capital: float, 
                               price: float, 
                               volatility: float = None,
                               method: PositionSizingMethod = PositionSizingMethod.FIXED,
                               params: Dict = None) -> float:
        """
        计算仓位
        
        Args:
            capital: 当前资金
            price: 当前价格
            volatility: 波动率（年化）
            method: 仓位计算方法
            params: 其他参数
        
        Returns:
            股数
        """
        params = params or {}
        
        if method == PositionSizingMethod.FIXED:
            # 固定仓位
            fixed_pct = params.get('pct', 0.5)
            return int(capital * fixed_pct / price)
        
        elif method == PositionSizingMethod.KELLY:
            # Kelly公式
            win_rate = params.get('win_rate', 0.5)
            avg_win = params.get('avg_win', 1.0)
            avg_loss = params.get('avg_loss', 1.0)
            
            if avg_loss == 0:
                return 0
            
            win_loss_ratio = avg_win / avg_loss
            kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
            
            # Kelly半仓更保守
            kelly_pct = max(0, kelly_pct * 0.5)
            kelly_pct = min(kelly_pct, self.max_position_pct)
            
            return int(capital * kelly_pct / price)
        
        elif method == PositionSizingMethod.VOLATILITY:
            # 波动率调整
            target_vol = params.get('target_vol', 0.15)  # 目标波动率15%
            
            if volatility is None or volatility == 0:
                volatility = 0.3  # 默认30%波动率
            
            vol_ratio = target_vol / volatility
            vol_pct = min(vol_ratio, self.max_position_pct)
            
            return int(capital * vol_pct / price)
        
        return int(capital * self.max_position_pct / price)
    
    def check_stop_loss(self, 
                       entry_price: float, 
                       current_price: float,
                       position_type: str = "long") -> bool:
        """
        检查是否触发止损
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_type: long/short
        
        Returns:
            是否触发止损
        """
        if position_type == "long":
            loss_pct = (entry_price - current_price) / entry_price
        else:
            loss_pct = (current_price - entry_price) / entry_price
        
        return loss_pct >= self.stop_loss_pct
    
    def check_take_profit(self, 
                         entry_price: float, 
                         current_price: float,
                         position_type: str = "long") -> bool:
        """
        检查是否触发止盈
        """
        if position_type == "long":
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price
        
        return profit_pct >= self.take_profit_pct
    
    def check_trailing_stop(self,
                          peak_price: float,
                          current_price: float,
                          position_type: str = "long") -> bool:
        """
        检查追踪止损
        """
        if position_type == "long":
            drawdown_pct = (peak_price - current_price) / peak_price
        else:
            drawdown_pct = (current_price - peak_price) / peak_price
        
        return drawdown_pct >= self.trailing_stop
    
    def update_drawdown(self, current_equity: float) -> Dict[str, float]:
        """
        更新回撤状态
        
        Returns:
            dict with current_drawdown, peak_equity
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        return {
            'current_drawdown': self.current_drawdown,
            'peak_equity': self.peak_equity,
            'max_drawdown_pct': self.max_drawdown_pct
        }
    
    def check_risk_limits(self, 
                         current_equity: float,
                         today_loss: float = 0) -> Dict[str, bool]:
        """
        检查风险限制
        
        Returns:
            dict of limit checks
        """
        drawdown_info = self.update_drawdown(current_equity)
        
        return {
            'max_drawdown_hit': drawdown_info['current_drawdown'] >= self.max_drawdown_pct,
            'daily_loss_hit': today_loss >= self.max_daily_loss_pct * current_equity,
            'can_trade': (drawdown_info['current_drawdown'] < self.max_drawdown_pct 
                         and today_loss < self.max_daily_loss_pct * current_equity)
        }


class PortfolioRiskManager:
    """
    组合风控管理器
    多策略组合时的风控
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.max_strategies = self.config.get('max_strategies', 10)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.7)
        
        # 各策略权重
        self.strategy_weights = {}
        self.strategy_returns = {}
    
    def calculate_weights(self, 
                         strategy_count: int,
                         returns: Dict[str, list] = None,
                         method: str = "equal") -> Dict[str, float]:
        """
        计算策略权重
        
        Args:
            strategy_count: 策略数量
            returns: 各策略历史收益
            method: equal/risk_parity
        """
        if method == "equal":
            weight = 1.0 / strategy_count
            return {f"strategy_{i}": weight for i in range(strategy_count)}
        
        elif method == "risk_parity" and returns:
            # 基于波动率的风险平价
            volatilities = {}
            for strat, ret in returns.items():
                if len(ret) > 0:
                    volatilities[strat] = np.std(ret) * np.sqrt(252)  # 年化
            
            # 波动率倒数作为权重
            total_inv_vol = sum(1/v for v in volatilities.values() if v > 0)
            weights = {}
            for strat, vol in volatilities.items():
                if vol > 0:
                    weights[strat] = (1/vol) / total_inv_vol
                else:
                    weights[strat] = 0
            
            return weights
        
        return {f"strategy_{i}": 1.0/strategy_count for i in range(strategy_count)}
    
    def check_diversification(self, weights: Dict[str, float]) -> bool:
        """
        检查分散度
        """
        if not weights:
            return False
        
        max_weight = max(weights.values())
        herfindahl = sum(w**2 for w in weights.values())
        
        # 单一策略不超过40%，HHI指数小于0.25
        return max_weight < 0.4 and herfindahl < 0.25
