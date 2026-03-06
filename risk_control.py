"""
风控模块 - 参考QUANTAXIS风控设计
完整风控体系
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


class RiskRule:
    """风控规则基类"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.triggered = False
    
    def check(self, account, order) -> bool:
        """检查是否触发"""
        if not self.enabled:
            return True
        return True
    
    def get_message(self) -> str:
        return f"{self.name}: OK"


class PositionLimitRule(RiskRule):
    """持仓限制"""
    
    def __init__(self, max_position_pct: float = 0.5):
        super().__init__("持仓限制")
        self.max_position_pct = max_position_pct
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        # 检查持仓比例
        position_value = account.position_value
        total_value = account.total_value
        
        if total_value > 0:
            position_pct = position_value / total_value
            if position_pct >= self.max_position_pct:
                self.triggered = True
                return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 持仓超过{self.max_position_pct*100}%"
        return f"{self.name}: OK"


class SingleOrderLimitRule(RiskRule):
    """单笔订单限制"""
    
    def __init__(self, max_order_value: float = 10000):
        super().__init__("单笔订单限制")
        self.max_order_value = max_order_value
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        order_value = order.price * order.volume
        if order_value > self.max_order_value:
            self.triggered = True
            return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 单笔超过{self.max_order_value}"
        return f"{self.name}: OK"


class DailyLossRule(RiskRule):
    """每日亏损限制"""
    
    def __init__(self, max_daily_loss_pct: float = 0.05):
        super().__init__("每日亏损限制")
        self.max_daily_loss_pct = max_daily_loss_pct
        self.daily_pnl = 0
        self.last_reset_date = None
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        today = datetime.now().date()
        
        # 重置
        if self.last_reset_date != today:
            self.daily_pnl = 0
            self.last_reset_date = today
        
        # 检查亏损
        if account.total_value < account.init_cash:
            loss_pct = (account.init_cash - account.total_value) / account.init_cash
            if loss_pct >= self.max_daily_loss_pct:
                self.triggered = True
                return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 亏损超过{self.max_daily_loss_pct*100}%"
        return f"{self.name}: OK"


class DrawdownRule(RiskRule):
    """回撤限制"""
    
    def __init__(self, max_drawdown_pct: float = 0.15):
        super().__init__("回撤限制")
        self.max_drawdown_pct = max_drawdown_pct
        self.peak_value = 0
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        # 更新峰值
        if account.total_value > self.peak_value:
            self.peak_value = account.total_value
        
        # 检查回撤
        if self.peak_value > 0:
            drawdown = (self.peak_value - account.total_value) / self.peak_value
            if drawdown >= self.max_drawdown_pct:
                self.triggered = True
                return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 回撤超过{self.max_drawdown_pct*100}%"
        return f"{self.name}: OK"


class ConsecutiveLossRule(RiskRule):
    """连亏限制"""
    
    def __init__(self, max_consecutive_losses: int = 3):
        super().__init__("连亏限制")
        self.max_consecutive_losses = max_consecutive_losses
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        if account.consecutive_losses >= self.max_consecutive_losses:
            self.triggered = True
            return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 连亏{self.max_consecutive_losses}次"
        return f"{self.name}: OK"


class TradingHoursRule(RiskRule):
    """交易时间限制"""
    
    def __init__(self, allowed_hours: List[int] = None):
        super().__init__("交易时间限制")
        self.allowed_hours = allowed_hours or [9, 10, 11, 13, 14, 15]
    
    def check(self, account, order) -> bool:
        if not self.enabled:
            return True
        
        now = datetime.now()
        hour = now.hour
        
        # 简单检查：是否在交易时间内
        if hour not in self.allowed_hours:
            # 允许市价单
            if order.price == 0:
                return True
            self.triggered = True
            return False
        
        return True
    
    def get_message(self) -> str:
        if self.triggered:
            return f"{self.name}: 触发 - 非交易时间"
        return f"{self.name}: OK"


class RiskController:
    """
    风控控制器
    
    参考 QUANTAXIS 风控体系
    """
    
    def __init__(self):
        self.rules: List[RiskRule] = []
        self.enabled = True
        self.log = []
        
        # 默认添加规则
        self.add_rule(PositionLimitRule(0.5))
        self.add_rule(SingleOrderLimitRule(10000))
        self.add_rule(DailyLossRule(0.05))
        self.add_rule(DrawdownRule(0.15))
        self.add_rule(ConsecutiveLossRule(3))
    
    def add_rule(self, rule: RiskRule):
        """添加规则"""
        self.rules.append(rule)
    
    def remove_rule(self, name: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != name]
    
    def check(self, account, order) -> tuple:
        """
        检查订单
        
        Returns:
            (allowed: bool, message: str)
        """
        if not self.enabled:
            return True, "风控未启用"
        
        messages = []
        
        for rule in self.rules:
            if not rule.check(account, order):
                messages.append(rule.get_message())
                self.log.append({
                    "time": datetime.now().isoformat(),
                    "rule": rule.name,
                    "triggered": True
                })
        
        if messages:
            return False, "; ".join(messages)
        
        return True, "风控通过"
    
    def get_status(self) -> Dict:
        """获取风控状态"""
        return {
            "enabled": self.enabled,
            "rules": len(self.rules),
            "active": sum(1 for r in self.rules if r.enabled),
            "triggered": sum(1 for r in self.rules if r.triggered),
            "log": self.log[-10:]
        }
    
    def reset(self):
        """重置"""
        for rule in self.rules:
            rule.triggered = False
        self.log = []


# 全局风控实例
_risk_controller: Optional[RiskController] = None


def get_risk_controller() -> RiskController:
    """获取风控实例"""
    global _risk_controller
    if _risk_controller is None:
        _risk_controller = RiskController()
    return _risk_controller


if __name__ == '__main__':
    # 测试
    from account import Account
    
    acc = Account("test", 100000)
    risk = get_risk_controller()
    
    print("风控状态:", risk.get_status())
