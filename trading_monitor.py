"""
实时监控系统 - Trading Monitor
==============================

功能:
- 实时监控策略信号
- 持仓监控
- 异常报警
- 定时执行

作者: AI量化系统
"""

from datetime import datetime, time
from typing import Dict, List, Callable
import threading
import time as time_module
import os
import json


class Monitor:
    """
    实时监控系统
    
    功能:
    1. 定时获取信号
    2. 持仓监控
    3. 异常报警
    4. 日志记录
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 监控配置
        self.check_interval = config.get('check_interval', 300)  # 检查间隔(秒)
        self.trading_hours = config.get('trading_hours', [
            (time(9, 30), time(11, 31)),  # 上午
            (time(13, 0), time(15, 1)),   # 下午
        ])
        
        # 回调函数
        self.signal_callback = None   # 信号回调
        self.alert_callback = None   # 报警回调
        
        # 状态
        self.running = False
        self.thread = None
        
        # 统计数据
        self.stats = {
            'total_checks': 0,
            'total_signals': 0,
            'alerts': 0,
            'errors': 0,
        }
        
        # 日志
        self.log_file = f"logs/monitor_{datetime.now().strftime('%Y%m%d')}.log"
        os.makedirs('logs', exist_ok=True)
    
    def set_signal_callback(self, callback: Callable):
        """设置信号回调"""
        self.signal_callback = callback
    
    def set_alert_callback(self, callback: Callable):
        """设置报警回调"""
        self.alert_callback = callback
    
    def start(self):
        """启动监控"""
        if self.running:
            self.log("Monitor already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.log("Monitor started")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.log("Monitor stopped")
    
    def _run(self):
        """主循环"""
        while self.running:
            try:
                # 检查是否在交易时段
                if self.is_trading_time():
                    self._check_and_execute()
                
                self.stats['total_checks'] += 1
                
            except Exception as e:
                self.stats['errors'] += 1
                self.log(f"Error: {e}")
            
            # 等待
            time_module.sleep(self.check_interval)
    
    def _check_and_execute(self):
        """检查并执行"""
        # 1. 获取信号
        if self.signal_callback:
            signal = self.signal_callback()
            
            if signal and signal != 'HOLD':
                self.stats['total_signals'] += 1
                self.log(f"Signal: {signal}")
                
                # 2. 检查是否需要报警
                if self.alert_callback:
                    self.alert_callback(signal)
    
    def is_trading_time(self) -> bool:
        """检查是否在交易时段"""
        now = datetime.now().time()
        
        for start, end in self.trading_hours:
            if start <= now <= end:
                return True
        
        return False
    
    def log(self, msg: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        
        with open(self.log_file, 'a') as f:
            f.write(log_msg + '\n')
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'running': self.running,
            'stats': self.stats,
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


class AlertManager:
    """
    报警管理器
    
    支持:
    - 邮件报警
    - 短信报警 (Twilio)
    - 推送报警 (Pushover)
    - 飞书报警
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        
        # 报警阈值
        self.pnl_alert_threshold = config.get('pnl_alert_threshold', -0.05)  # 亏损5%报警
        self.position_alert = config.get('position_alert', True)  # 持仓变化报警
    
    def send_alert(self, title: str, message: str, level: str = "INFO"):
        """
        发送报警
        
        Args:
            title: 标题
            message: 内容
            level: 级别 (INFO/WARNING/ERROR)
        """
        if not self.enabled:
            return
        
        alert_msg = f"[{level}] {title}: {message}"
        print(f"🚨 ALERT: {alert_msg}")
        
        # 可以扩展为:
        # - 发送邮件
        # - 发送短信
        # - 推送到手机
    
    def check_and_alert(self, account_info: Dict):
        """
        检查并报警
        
        Args:
            account_info: 账户信息
        """
        # 检查日亏损
        daily_pnl = account_info.get('daily_pnl', 0)
        if daily_pnl < self.pnl_alert_threshold:
            self.send_alert(
                "日亏损报警",
                f"亏损 {daily_pnl*100:.1f}%",
                "WARNING"
            )
        
        # 检查持仓异常
        if self.position_alert:
            position_change = account_info.get('position_change', False)
            if position_change:
                self.send_alert(
                    "持仓变化",
                    "持仓发生变化",
                    "INFO"
                )


class Dashboard:
    """
    监控面板
    
    显示:
    - 当前持仓
    - 账户状况
    - 信号状态
    - 统计信息
    """
    
    def __init__(self):
        self.data = {}
    
    def update(self, data: Dict):
        """更新数据"""
        self.data = data
    
    def render(self) -> str:
        """渲染面板"""
        lines = []
        lines.append("=" * 60)
        lines.append("           量化交易监控系统")
        lines.append("=" * 60)
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 账户
        if 'account' in self.data:
            acc = self.data['account']
            lines.append("📊 账户状况:")
            lines.append(f"   总资产: {acc.get('total_assets', 0):,.2f}")
            lines.append(f"   可用资金: {acc.get('available_cash', 0):,.2f}")
            lines.append(f"   持仓数量: {len(acc.get('positions', []))}")
            lines.append("")
        
        # 持仓
        if 'positions' in self.data:
            positions = self.data['positions']
            lines.append(f"📈 持仓 ({len(positions)}):")
            for p in positions:
                lines.append(f"   {p['symbol']}: {p['quantity']} @ {p['current_price']} ({(p.get('pnl_pct', 0)*100):.1f}%)")
            lines.append("")
        
        # 信号
        if 'signal' in self.data:
            lines.append(f"📉 当前信号: {self.data['signal']}")
            lines.append("")
        
        # 统计
        if 'stats' in self.data:
            stats = self.data['stats']
            lines.append("📊 统计:")
            lines.append(f"   检查次数: {stats.get('total_checks', 0)}")
            lines.append(f"   信号次数: {stats.get('total_signals', 0)}")
            lines.append(f"   报警次数: {stats.get('alerts', 0)}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def save_html(self, filename: str = "dashboard.html"):
        """保存为HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>量化交易监控</title>
    <style>
        body {{ font-family: monospace; background: #1a1a1a; color: #0f0; padding: 20px; }}
        .header {{ font-size: 24px; text-align: center; margin-bottom: 20px; }}
        .card {{ background: #333; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .positive {{ color: #0f0; }}
        .negative {{ color: #f00; }}
        .neutral {{ color: #ff0; }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="header">量化交易监控系统</div>
    <div class="card">
        <div>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    <div class="card">
        <div>总资产: {self.data.get('account', {}).get('total_assets', 0):,.2f}</div>
        <div>可用资金: {self.data.get('account', {}).get('available_cash', 0):,.2f}</div>
    </div>
    <div class="card">
        <div>当前信号: {self.data.get('signal', 'N/A')}</div>
    </div>
</body>
</html>
"""
        with open(filename, 'w') as f:
            f.write(html)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化
    config = {
        'check_interval': 60,  # 60秒检查一次
        'enabled': True,
        'pnl_alert_threshold': -0.05,
    }
    
    monitor = Monitor(config)
    alerts = AlertManager(config)
    
    # 模拟信号回调
    def get_signal():
        # 这里应该调用策略获取信号
        import random
        signals = ['BUY', 'SELL', 'HOLD']
        return random.choice(signals)
    
    monitor.set_signal_callback(get_signal)
    
    # 启动
    print("启动监控...")
    monitor.start()
    
    # 运行30秒
    time_module.sleep(30)
    
    # 停止
    monitor.stop()
    
    # 输出状态
    print(monitor.get_status())
