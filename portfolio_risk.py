#!/usr/bin/env python3
"""
组合风控模块
多资产组合层面的风险管理与监控
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Position:
    """持仓"""
    symbol: str
    market: str  # crypto, us_stock, cn_stock
    quantity: float
    avg_price: float
    current_price: float = 0
    
    @property
    def value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost(self) -> float:
        return self.quantity * self.avg_price
    
    @property
    def pnl(self) -> float:
        return self.value - self.cost
    
    @property
    def pnl_pct(self) -> float:
        if self.cost == 0:
            return 0
        return self.pnl / self.cost


@dataclass
class RiskLimit:
    """风险限额"""
    max_total_exposure: float = 1.0      # 最大总敞口 (占总资产比例)
    max_single_position: float = 0.3     # 最大单一持仓比例
    max_correlation: float = 0.7          # 最大持仓相关性
    max_leverage: float = 3.0
aily_loss: float = 0.05          # 最大日亏损 (5%)
    max_drawdown: float = 0.15            # 最大回撤 (15%)
    min_diversification: int = 3          # 最小分散度 (持仓数)


class PortfolioRiskManager:
    """
    组合风控管理器
    
    功能:
    - 组合整体风险监控
    - 持仓限额检查
    - 分散度检查
    - 相关性监控
    - 爆仓风险预警
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.limits = RiskLimit(
            max_total_exposure=self.config.get('max_total_exposure', 1.0),
            max_single_position=self.config.get('max_single_position', 0.3),
            max_daily_loss=self.config.get('max_daily_loss', 0.05),
            max_drawdown=self.config.get('max_drawdown', 0.15),
        )
        
        self.positions: List[Position] = []
        self.total_value = 0
        self.cash = 0
        
        # 历史记录
        self.peak_value = 0
        self.daily_pnl = 0
        self.risk_events: List[Dict] = []
        
        # 记录文件
        self.log_dir = "/root/.openclaw/workspace/quant/quant/logs"
        self.risk_log_file = f"{self.log_dir}/portfolio_risk.json"
    
    def update_positions(self, positions: List[Dict], cash: float = 0):
        """
        更新持仓
        
        Args:
            positions: 持仓列表 [{
                'symbol': 'BTC',
                'market': 'crypto',
                'quantity': 0.5,
                'avg_price': 45000,
                'current_price': 50000
            }]
            cash: 现金
        """
        self.positions = [Position(**p) for p in positions]
        self.cash = cash
        self.total_value = sum(p.value for p in self.positions) + cash
        
        # 更新峰值
        if self.total_value > self.peak_value:
            self.peak_value = self.total_value
    
    def calculate_exposure(self) -> Dict:
        """计算各市场敞口"""
        exposure = {
            'crypto': 0,
            'us_stock': 0,
            'cn_stock': 0,
            'total': 0
        }
        
        if self.total_value == 0:
            return exposure
        
        for pos in self.positions:
            if pos.market in exposure:
                exposure[pos.market] += pos.value
        
        exposure['total'] = sum(
            v for k, v in exposure.items() if k != 'total'
        )
        
        # 转为比例
        for k in exposure:
            exposure[f'{k}_pct'] = exposure[k] / self.total_value
        
        return exposure
    
    def check_position_limits(self) -> Dict:
        """检查持仓限额"""
        violations = []
        
        if self.total_value == 0:
            return {'ok': True, 'violations': []}
        
        # 检查单一持仓
        for pos in self.positions:
            pos_pct = pos.value / self.total_value
            
            if pos_pct > self.limits.max_single_position:
                violations.append({
                    'type': 'single_position',
                    'symbol': pos.symbol,
                    'current': f"{pos_pct:.1%}",
                    'limit': f"{self.limits.max_single_position:.1%}",
                    'severity': 'high'
                })
        
        # 检查总敞口
        exposure = self.calculate_exposure()
        total_exposure_pct = exposure.get('total_pct', 0)
        
        if total_exposure_pct > self.limits.max_total_exposure:
            violations.append({
                'type': 'total_exposure',
                'current': f"{total_exposure_pct:.1%}",
                'limit': f"{self.limits.max_total_exposure:.1%}",
                'severity': 'high'
            })
        
        return {
            'ok': len(violations) == 0,
            'violations': violations
        }
    
    def check_diversification(self) -> Dict:
        """检查分散度"""
        n_positions = len(self.positions)
        
        if n_positions < self.limits.min_diversification:
            return {
                'ok': False,
                'current': n_positions,
                'required': self.limits.min_diversification,
                'message': f"持仓分散度不足: {n_positions} < {self.limits.min_diversification}",
                'severity': 'medium'
            }
        
        # 检查持仓是否过于集中
        if self.total_value > 0:
            for pos in self.positions:
                pos_pct = pos.value / self.total_value
                if pos_pct > 0.5:
                    return {
                        'ok': False,
                        'message': f"持仓过于集中: {pos.symbol} 占比 {pos_pct:.1%}",
                        'severity': 'high'
                    }
        
        return {'ok': True, 'current': n_positions}
    
    def calculate_var(self, confidence: float = 0.95) -> float:
        """
        计算VaR (Value at Risk)
        
        Args:
            confidence: 置信度
        
        Returns:
            风险价值 (可能的最大损失)
        """
        if not self.positions or self.total_value == 0:
            return 0
        
        # 简化的VaR计算 (基于持仓波动)
        # 实际应该用历史数据计算
        var = 0
        
        # 假设各资产的波动率
        volatility = {
            'crypto': 0.80,    # 数字货币 80%
            'us_stock': 0.20,   # 美股 20%
            'cn_stock': 0.25,   # A股 25%
        }
        
        for pos in self.positions:
            vol = volatility.get(pos.market, 0.20)
            pos_var = pos.value * vol * 1.65  # 95%置信度
            var += pos_var
        
        return var
    
    def check_drawdown(self) -> Dict:
        """检查回撤"""
        if self.peak_value == 0 or self.total_value == 0:
            return {'ok': True, 'drawdown': 0}
        
        drawdown = (self.peak_value - self.total_value) / self.peak_value
        
        if drawdown > self.limits.max_drawdown:
            return {
                'ok': False,
                'drawdown': f"{drawdown:.1%}",
                'limit': f"{self.limits.max_drawdown:.1%}",
                'severity': 'critical',
                'message': f"回撤超过限制: {drawdown:.1%} > {self.limits.max_drawdown:.1%}"
            }
        
        return {
            'ok': True,
            'drawdown': f"{drawdown:.1%}",
            'peak': f"{self.peak_value:.2f}",
            'current': f"{self.total_value:.2f}"
        }
    
    def check_daily_loss(self, yesterday_value: float) -> Dict:
        """检查日内亏损"""
        if yesterday_value == 0:
            return {'ok': True}
        
        daily_loss = (yesterday_value - self.total_value) / yesterday_value
        
        if daily_loss > self.limits.max_daily_loss:
            return {
                'ok': False,
                'daily_loss': f"{daily_loss:.1%}",
                'limit': f"{self.limits.max_daily_loss:.1%}",
                'severity': 'critical',
                'message': f"日内亏损超限: {daily_loss:.1%} > {self.limits.max_daily_loss:.1%}"
            }
        
        return {
            'ok': True,
            'daily_loss': f"{daily_loss:.1%}"
        }
    
    def generate_risk_report(self, yesterday_value: float = 0) -> Dict:
        """
        生成完整风控报告
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio': {
                'total_value': round(self.total_value, 2),
                'cash': round(self.cash, 2),
                'positions_count': len(self.positions),
                'peak_value': round(self.peak_value, 2)
            },
            'exposure': self.calculate_exposure(),
            'position_limits': self.check_position_limits(),
            'diversification': self.check_diversification(),
            'drawdown': self.check_drawdown(),
            'var_95': round(self.calculate_var(0.95), 2)
        }
        
        if yesterday_value > 0:
            report['daily_loss'] = self.check_daily_loss(yesterday_value)
        
        # 汇总
        all_ok = (
            report['position_limits']['ok'] and
            report['diversification']['ok'] and
            report['drawdown']['ok'] and
            report['daily_loss']['ok'] if yesterday_value > 0 else True
        )
        
        report['overall'] = {
            'status': 'ok' if all_ok else 'warning',
            'risk_level': self._calculate_risk_level(report)
        }
        
        return report
    
    def _calculate_risk_level(self, report: Dict) -> str:
        """计算风险等级"""
        violations = report['position_limits'].get('violations', [])
        
        if not report['drawdown']['ok']:
            return 'critical'
        
        if violations:
            high_severity = any(v.get('severity') == 'high' for v in violations)
            if high_severity:
                return 'high'
            return 'medium'
        
        if not report['diversification']['ok']:
            return 'medium'
        
        return 'low'
    
    def log_risk_event(self, event_type: str, message: str, severity: str = 'info'):
        """记录风险事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'severity': severity
        }
        self.risk_events.append(event)
        
        # 保存到文件
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 读取现有事件
        events = []
        if os.path.exists(self.risk_log_file):
            try:
                with open(self.risk_log_file, 'r') as f:
                    events = json.load(f)
            except:
                events = []
        
        events.append(event)
        
        # 只保留最近100条
        events = events[-100:]
        
        with open(self.risk_log_file, 'w') as f:
            json.dump(events, f, indent=2)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 模拟持仓
    positions = [
        {'symbol': 'BTC', 'market': 'crypto', 'quantity': 0.5, 'avg_price': 45000, 'current_price': 50000},
        {'symbol': 'SPY', 'market': 'us_stock', 'quantity': 100, 'avg_price': 450, 'current_price': 480},
        {'symbol': 'QQQ', 'market': 'us_stock', 'quantity': 50, 'avg_price': 380, 'current_price': 400},
    ]
    
    # 创建风控管理器
    pm = PortfolioRiskManager()
    pm.update_positions(positions, cash=10000)
    
    # 生成报告
    report = pm.generate_risk_report(yesterday_value=95000)
    
    print("=" * 50)
    print("组合风控报告")
    print("=" * 50)
    print(json.dumps(report, indent=2, ensure_ascii=False))
