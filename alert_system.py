#!/usr/bin/env python3
"""
实时预警系统
多维度监控 + 自动触发告警
"""

import os
import sys
import time
import json
from typing import Dict, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    PRICE = "price"           # 价格告警
    VOLUME = "volume"         # 成交量告警
    SIGNAL = "signal"         # 信号告警
    RISK = "risk"            # 风控告警
    SYSTEM = "system"         # 系统告警
    TREND = "trend"          # 趋势告警


@dataclass
class Alert:
    """告警"""
    level: AlertLevel
    type: AlertType
    title: str
    message: str
    data: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AlertRule:
    """告警规则"""
    def __init__(self, name: str, alert_type: AlertType, level: AlertLevel):
        self.name = name
        self.alert_type = alert_type
        self.level = level
        self.enabled = True
        self.callbacks: List[Callable] = []
    
    def check(self, data: Dict) -> bool:
        """检查是否触发告警 - 子类实现"""
        raise NotImplementedError
    
    def on_trigger(self, alert: Alert):
        """触发时的回调"""
        for cb in self.callbacks:
            try:
                cb(alert)
            except Exception as e:
                print(f"Callback error: {e}")


class PriceAlertRule(AlertRule):
    """价格告警规则"""
    def __init__(self, name: str, symbol: str, price_threshold: float, condition: str = "above"):
        super().__init__(name, AlertType.PRICE, AlertLevel.WARNING)
        self.symbol = symbol
        self.price_threshold = price_threshold
        self.condition = condition  # above, below, change
    
    def check(self, data: Dict) -> bool:
        if data.get('symbol') != self.symbol:
            return False
        
        current_price = data.get('price', 0)
        
        if self.condition == "above":
            return current_price > self.price_threshold
        elif self.condition == "below":
            return current_price < self.price_threshold
        elif self.condition == "change":
            change_pct = abs(data.get('change_24h', 0))
            return change_pct > self.price_threshold
        
        return False


class RiskAlertRule(AlertRule):
    """风控告警规则"""
    def __init__(self, name: str, metric: str, threshold: float, level: AlertLevel = AlertLevel.ERROR):
        super().__init__(name, AlertType.RISK, level)
        self.metric = metric
        self.threshold = threshold
    
    def check(self, data: Dict) -> bool:
        value = data.get(self.metric, 0)
        
        if self.metric in ['drawdown', 'max_drawdown']:
            return abs(value) > self.threshold
        elif self.metric in ['risk_score']:
            return value > self.threshold
        elif self.metric in ['loss_streak']:
            return value >= self.threshold
        
        return False


class AlertManager:
    """
    告警管理器
    
    功能:
    - 规则管理
    - 告警检查
    - 告警记录
    - 多渠道通知
    """
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self.max_alerts = 1000
        
        # 通知回调
        self.notification_callbacks: List[Callable] = []
        
        # 默认规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认规则"""
        # 价格告警
        self.add_rule(PriceAlertRule("BTC大涨", "BTCUSDT", 5, "change"))
        self.add_rule(PriceAlertRule("BTC大跌", "BTCUSDT", -5, "change"))
        
        # 风控告警
        self.add_rule(RiskAlertRule("回撤过大", "drawdown", 0.10, AlertLevel.ERROR))
        self.add_rule(RiskAlertRule("风险评分高", "risk_score", 80, AlertLevel.WARNING))
        self.add_rule(RiskAlertRule("连亏过多", "loss_streak", 3, AlertLevel.ERROR))
    
    def add_rule(self, rule: AlertRule):
        """添加规则"""
        self.rules.append(rule)
    
    def remove_rule(self, name: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != name]
    
    def enable_rule(self, name: str, enabled: bool = True):
        """启用/禁用规则"""
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = enabled
    
    def check(self, data: Dict) -> List[Alert]:
        """检查所有规则"""
        triggered = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.check(data):
                    alert = Alert(
                        level=rule.level,
                        type=rule.alert_type,
                        title=rule.name,
                        message=f"{rule.name} 触发条件: {data}",
                        data=data
                    )
                    triggered.append(alert)
                    rule.on_trigger(alert)
            except Exception as e:
                print(f"Rule check error {rule.name}: {e}")
        
        return triggered
    
    def trigger(self, alert: Alert):
        """触发告警"""
        self.alerts.append(alert)
        
        # 保持告警数量
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # 通知回调
        for cb in self.notification_callbacks:
            try:
                cb(alert)
            except Exception as e:
                print(f"Notification error: {e}")
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self.notification_callbacks.append(callback)
    
    def get_alerts(self, level: AlertLevel = None, alert_type: AlertType = None, 
                   n: int = 50) -> List[Alert]:
        """获取告警历史"""
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]
        
        return alerts[-n:]
    
    def get_stats(self) -> Dict:
        """获取告警统计"""
        stats = {
            'total': len(self.alerts),
            'by_level': {},
            'by_type': {}
        }
        
        for alert in self.alerts:
            level = alert.level.value
            alert_type = alert.type.value
            
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
            stats['by_type'][alert_type] = stats['by_type'].get(alert_type, 0) + 1
        
        return stats


class MonitorRunner:
    """监控运行器"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.running = False
        self.thread = None
    
    def start(self, interval: int = 60):
        """启动监控"""
        self.running = True
        self.interval = interval
        
        def run():
            while self.running:
                try:
                    self._check()
                except Exception as e:
                    print(f"Monitor error: {e}")
                time.sleep(self.interval)
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止监控"""
        self.running = False
    
    def _check(self):
        """检查 - 获取最新数据"""
        try:
            # 获取账户数据
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 获取价格
            ticker = client.get_symbol_ticker(symbol="BTCUSDT")
            price = float(ticker['price'])
            
            # 获取24h统计
            stats = client.get_ticker(symbol="BTCUSDT")
            change_24h = float(stats['priceChangePercent'])
            
            # 构建数据
            data = {
                'symbol': 'BTCUSDT',
                'price': price,
                'change_24h': change_24h,
                'volume': float(stats['volume']),
            }
            
            # 检查规则
            alerts = self.alert_manager.check(data)
            
            # 触发告警
            for alert in alerts:
                self.alert_manager.trigger(alert)
                print(f"🚨 [{alert.level.value}] {alert.title}: {alert.message}")
                
        except Exception as e:
            print(f"Data fetch error: {e}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("实时预警系统")
    print("=" * 50)
    
    # 创建告警管理器
    am = AlertManager()
    
    # 添加自定义规则
    def on_alert(alert):
        print(f"收到告警: {alert.title}")
    
    am.on_alert(on_alert)
    
    # 测试数据
    test_data = {
        'symbol': 'BTCUSDT',
        'price': 52000,
        'change_24h': 6.5,
        'drawdown': 0.12,
        'risk_score': 85,
        'loss_streak': 4
    }
    
    # 检查
    alerts = am.check(test_data)
    
    print(f"\n触发告警数: {len(alerts)}")
    for alert in alerts:
        print(f"  - [{alert.level.value}] {alert.title}")
    
    # 统计
    print("\n告警统计:")
    print(am.get_stats())
