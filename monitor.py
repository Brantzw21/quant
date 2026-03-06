"""
日志与监控模块
交易日志、异常告警、系统监控
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import smtplib
from email.mime.text import MIMEText


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class TradingLogger:
    """
    交易日志记录器
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 文件日志
        self.log_file = os.path.join(log_dir, "trading.log")
        
        # 交易日志
        self.trade_log_file = os.path.join(log_dir, "trades.json")
        
        # 系统日志
        self.system_log_file = os.path.join(log_dir, "system.log")
        
        # 初始化logger
        self.logger = logging.getLogger("quant")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)
        
        # console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def log_trade(self, trade: Dict):
        """记录交易"""
        # 读取现有日志
        trades = []
        if os.path.exists(self.trade_log_file):
            try:
                with open(self.trade_log_file, 'r') as f:
                    trades = json.load(f)
            except:
                trades = []
        
        # 添加新交易
        trades.append({
            **trade,
            'timestamp': datetime.now().isoformat()
        })
        
        # 保存
        with open(self.trade_log_file, 'w') as f:
            json.dump(trades, f, indent=2)
        
        self.info(f"交易记录: {trade.get('action')} {trade.get('symbol')} @ {trade.get('price')}")
    
    def log_signal(self, signal: Dict):
        """记录信号"""
        self.info(f"信号: {signal.get('signal')} - {signal.get('reason')}")
    
    def log_error(self, error: str, context: Dict = None):
        """记录错误"""
        error_record = {
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        # 保存到错误日志
        error_file = os.path.join(self.log_dir, "errors.json")
        errors = []
        if os.path.exists(error_file):
            try:
                with open(error_file, 'r') as f:
                    errors = json.load(f)
            except:
                errors = []
        
        errors.append(error_record)
        
        # 只保留最近100条
        errors = errors[-100:]
        
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        
        self.logger.error(f"错误: {error}")
    
    def get_trades(self, days: int = 7) -> List[Dict]:
        """获取交易记录"""
        if not os.path.exists(self.trade_log_file):
            return []
        
        with open(self.trade_log_file, 'r') as f:
            trades = json.load(f)
        
        # 过滤日期
        if days > 0:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            trades = [t for t in trades if t.get('timestamp', '') > cutoff]
        
        return trades
    
    def get_summary(self, days: int = 7) -> Dict:
        """获取日志摘要"""
        trades = self.get_trades(days)
        
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = sum(1 for t in trades if t.get('pnl', 0) < 0)
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        return {
            'total_trades': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / len(trades) * 100, 2) if trades else 0,
            'total_pnl': round(total_pnl, 2)
        }


class AlertManager:
    """
    告警管理器
    """
    
    def __init__(self):
        self.alerts = []
        self.email_config = None
    
    def set_email(self, smtp_server: str, port: int, 
                  username: str, password: str, to_addrs: List[str]):
        """设置邮件告警"""
        self.email_config = {
            'smtp_server': smtp_server,
            'port': port,
            'username': username,
            'password': password,
            'to_addrs': to_addrs
        }
    
    def send_alert(self, title: str, message: str, level: str = "INFO"):
        """发送告警"""
        alert = {
            'title': title,
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        
        # 打印日志
        print(f"[{level}] {title}: {message}")
        
        # 发送邮件
        if self.email_config and level in ['ERROR', 'CRITICAL']:
            self._send_email(title, message)
    
    def _send_email(self, title: str, message: str):
        """发送邮件"""
        if not self.email_config:
            return
        
        try:
            msg = MIMEText(message, 'plain', 'utf-8')
            msg['Subject'] = f"[Quant] {title}"
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(self.email_config['to_addrs'])
            
            server = smtplib.SMTP(
                self.email_config['smtp_server'],
                self.email_config['port']
            )
            server.starttls()
            server.login(
                self.email_config['username'],
                self.email_config['password']
            )
            server.send_message(msg)
            server.quit()
            
            print("邮件告警已发送")
        except Exception as e:
            print(f"邮件发送失败: {e}")
    
    def check_and_alert(self, account, config: Dict):
        """
        检查并告警
        
        Args:
            account: 账户对象
            config: 告警配置
        """
        # 检查回撤
        if config.get('max_drawdown'):
            # 简化实现
            pass
        
        # 检查连亏
        if config.get('consecutive_losses'):
            pass
        
        # 检查异常交易
        if config.get('suspicious_trades'):
            pass


class SystemMonitor:
    """
    系统监控
    """
    
    def __init__(self):
        self.metrics = {}
        self.start_time = datetime.now()
    
    def record_metric(self, name: str, value: float):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_metric(self, name: str, hours: int = 1) -> List[Dict]:
        """获取指标"""
        if name not in self.metrics:
            return []
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        return [m for m in self.metrics[name] if m['timestamp'] > cutoff]
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'uptime_seconds': round(uptime, 0),
            'uptime_hours': round(uptime / 3600, 1),
            'metrics_count': len(self.metrics),
            'start_time': self.start_time.isoformat()
        }


# 全局实例
_logger: Optional[TradingLogger] = None
_alert_manager: Optional[AlertManager] = None
_monitor: Optional[SystemMonitor] = None


def get_logger() -> TradingLogger:
    global _logger
    if _logger is None:
        _logger = TradingLogger()
    return _logger


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_system_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor


if __name__ == '__main__':
    # 测试
    logger = get_logger()
    logger.info("测试日志")
    logger.log_trade({
        'action': 'BUY',
        'symbol': 'BTC/USDT',
        'price': 50000,
        'volume': 0.1
    })
    
    print(logger.get_summary())
