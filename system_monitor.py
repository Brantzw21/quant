#!/usr/bin/env python3
"""
系统监控模块
监控服务器资源、进程、日志等
"""

import os
import sys
import json
import time
import psutil
import subprocess
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    timestamp: str


class SystemMonitor:
    """
    系统监控器
    
    功能:
    - CPU/内存/磁盘监控
    - 进程监控
    - 异常检测
    - 告警通知
    """
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.alert_thresholds = {
            'cpu': 80,        # CPU > 80% 告警
            'memory': 85,     # 内存 > 85% 告警
            'disk': 90,       # 磁盘 > 90% 告警
        }
        
        # 网络IO基准
        self._last_net_io = None
        self._last_time = None
    
    def get_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存
        memory = psutil.virtual_memory()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        
        # 网络
        net_io = psutil.net_io_counters()
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            network_sent=net_io.bytes_sent,
            network_recv=net_io.bytes_recv,
            timestamp=datetime.now().isoformat()
        )
    
    def get_processes(self, top_n: int = 10) -> List[Dict]:
        """获取进程列表"""
        processes = []
        
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = p.info
                if pinfo['cpu_percent'] is None:
                    pinfo['cpu_percent'] = 0
                if pinfo['memory_percent'] is None:
                    pinfo['memory_percent'] = 0
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按CPU排序
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        
        return processes[:top_n]
    
    def check_alerts(self) -> List[Dict]:
        """检查告警"""
        metrics = self.get_metrics()
        alerts = []
        
        # CPU告警
        if metrics.cpu_percent > self.alert_thresholds['cpu']:
            alerts.append({
                'type': 'cpu',
                'level': 'warning',
                'message': f"CPU使用率过高: {metrics.cpu_percent:.1f}%",
                'value': metrics.cpu_percent,
                'threshold': self.alert_thresholds['cpu']
            })
        
        # 内存告警
        if metrics.memory_percent > self.alert_thresholds['memory']:
            alerts.append({
                'type': 'memory',
                'level': 'warning',
                'message': f"内存使用率过高: {metrics.memory_percent:.1f}%",
                'value': metrics.memory_percent,
                'threshold': self.alert_thresholds['memory']
            })
        
        # 磁盘告警
        if metrics.disk_percent > self.alert_thresholds['disk']:
            alerts.append({
                'type': 'disk',
                'level': 'critical',
                'message': f"磁盘空间不足: {metrics.disk_percent:.1f}%",
                'value': metrics.disk_percent,
                'threshold': self.alert_thresholds['disk']
            })
        
        self.alerts = alerts
        return alerts
    
    def get_server_info(self) -> Dict:
        """获取服务器信息"""
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        
        return {
            'hostname': os.uname().nodename,
            'platform': sys.platform,
            'python_version': sys.version.split()[0],
            'uptime_hours': round(uptime / 3600, 1),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    
    def get_port_process(self, port: int) -> Dict:
        """获取占用指定端口的进程"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    return {
                        'pid': conn.pid,
                        'name': proc.name(),
                        'status': proc.status(),
                        'cpu': proc.cpu_percent(),
                        'memory': proc.memory_percent()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return {}
    
    def get_system_report(self) -> Dict:
        """生成完整系统报告"""
        metrics = self.get_metrics()
        alerts = self.check_alerts()
        
        return {
            'timestamp': metrics.timestamp,
            'server': self.get_server_info(),
            'metrics': {
                'cpu': f"{metrics.cpu_percent:.1f}%",
                'memory': f"{metrics.memory_percent:.1f}%",
                'disk': f"{metrics.disk_percent:.1f}%",
            },
            'alerts': alerts,
            'status': 'critical' if any(a['level'] == 'critical' for a in alerts) 
                     else 'warning' if alerts else 'ok'
        }
    
    def check_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return False
        return True
    
    def get_quant_processes(self) -> List[Dict]:
        """获取Quant相关进程"""
        quant_processes = []
        
        # 关键词
        keywords = ['python', 'node', 'flask', 'gunicorn', 'vite']
        
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = p.info
                name = pinfo.get('name', '').lower()
                cmdline = ' '.join(pinfo.get('cmdline', [])).lower()
                
                # 检查是否Quant相关
                if any(kw in name or kw in cmdline for kw in keywords):
                    if 'quant' in cmdline or 'dashboard' in cmdline or 'trade' in cmdline:
                        quant_processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo.get('name', ''),
                            'cmdline': ' '.join(pinfo.get('cmdline', [])[:3]),
                            'cpu': pinfo.get('cpu_percent', 0),
                            'memory': pinfo.get('memory_percent', 0)
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return quant_processes


# ==================== 使用示例 ====================

if __name__ == "__main__":
    monitor = SystemMonitor()
    
    print("=" * 50)
    print("系统监控报告")
    print("=" * 50)
    
    # 服务器信息
    info = monitor.get_server_info()
    print(f"\n服务器: {info['hostname']}")
    print(f"运行时间: {info['uptime_hours']} 小时")
    print(f"负载: {info['load_avg']}")
    
    # 系统指标
    metrics = monitor.get_metrics()
    print(f"\nCPU: {metrics.cpu_percent:.1f}%")
    print(f"内存: {metrics.memory_percent:.1f}%")
    print(f"磁盘: {metrics.disk_percent:.1f}%")
    
    # 检查告警
    alerts = monitor.check_alerts()
    if alerts:
        print("\n⚠️ 告警:")
        for a in alerts:
            print(f"  [{a['level']}] {a['message']}")
    else:
        print("\n✅ 系统正常")
    
    # Quant进程
    print("\nQuant相关进程:")
    procs = monitor.get_quant_processes()
    for p in procs[:5]:
        print(f"  PID {p['pid']}: {p['name']} (CPU: {p['cpu']:.1f}%)")
