#!/usr/bin/env python3
"""
Cron 定时任务调度器
支持多种交易场景的定时执行
"""

import os
import sys
import time
import json
import schedule
import threading
from typing import Dict, List, Callable, Any
from datetime import datetime, time as dt_time
from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    SIGNAL = "signal"       # 生成信号
    TRADE = "trade"        # 执行交易
    REPORT = "report"       # 发送报告
    BACKUP = "backup"      # 数据备份
    CHECK = "check"         # 健康检查


@dataclass
class Task:
    """任务"""
    name: str
    task_type: TaskType
    func: Callable
    interval: int = 0  # 秒 (与cron_time二选一)
    cron_time: str = ""  # cron格式 HH:MM
    enabled: bool = True
    description: str = ""
    
    last_run: str = ""
    next_run: str = ""
    run_count: int = 0
    error_count: int = 0


class TaskScheduler:
    """
    定时任务调度器
    
    功能:
    - 定时执行任务
    - 任务管理
    - 执行记录
    - 错误处理
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.thread = None
        
        # 记录
        self.history: List[Dict] = []
        self.max_history = 1000
    
    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.name] = task
        
        # 注册到schedule
        if task.interval > 0:
            # 间隔任务
            getattr(schedule, f"every_{task.interval}_seconds")(self._create_wrapper(task))
        elif task.cron_time:
            # 定时任务
            hour, minute = task.cron_time.split(':')
            schedule.every().day.at(f"{hour}:{minute}").do(self._create_wrapper(task))
    
    def _create_wrapper(self, task: Task):
        """创建任务包装器"""
        def wrapper():
            self._run_task(task)
        return wrapper
    
    def _run_task(self, task: Task):
        """执行任务"""
        if not task.enabled:
            return
        
        start_time = datetime.now()
        
        try:
            # 执行任务
            result = task.func()
            
            # 成功
            task.last_run = start_time.isoformat()
            task.run_count += 1
            
            self._log(task, "success", result)
            
            return result
            
        except Exception as e:
            # 失败
            task.error_count += 1
            
            self._log(task, "error", str(e))
            
            print(f"❌ Task {task.name} failed: {e}")
    
    def _log(self, task: Task, status: str, message: Any):
        """记录执行日志"""
        entry = {
            'time': datetime.now().isoformat(),
            'task': task.name,
            'type': task.task_type.value,
            'status': status,
            'message': str(message)[:200],
            'run_count': task.run_count,
            'error_count': task.error_count
        }
        
        self.history.append(entry)
        
        # 保持记录数量
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def enable_task(self, name: str, enabled: bool = True):
        """启用/禁用任务"""
        if name in self.tasks:
            self.tasks[name].enabled = enabled
    
    def remove_task(self, name: str):
        """移除任务"""
        if name in self.tasks:
            del self.tasks[name]
            schedule.clear(name)
    
    def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        
        def run():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        
        print(f"✅ 调度器启动, {len(self.tasks)} 个任务")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        schedule.clear()
        print("⏹️ 调度器已停止")
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'running': self.running,
            'task_count': len(self.tasks),
            'enabled_count': sum(1 for t in self.tasks.values() if t.enabled),
            'total_runs': sum(t.run_count for t in self.tasks.values()),
            'total_errors': sum(t.error_count for t in self.tasks.values())
        }
    
    def get_tasks(self) -> List[Dict]:
        """获取任务列表"""
        return [
            {
                'name': t.name,
                'type': t.task_type.value,
                'enabled': t.enabled,
                'interval': t.interval,
                'cron_time': t.cron_time,
                'last_run': t.last_run,
                'run_count': t.run_count,
                'error_count': t.error_count,
                'description': t.description
            }
            for t in self.tasks.values()
        ]
    
    def get_history(self, n: int = 50) -> List[Dict]:
        """获取执行历史"""
        return self.history[-n:]


# ==================== 预设任务 ====================

def create_signal_task(scheduler: TaskScheduler):
    """创建信号生成任务"""
    
    def run():
        from multi_signal import SignalGenerator
        generator = SignalGenerator()
        signals = generator.generate_all_signals()
        
        # 保存
        generator.save_signals()
        
        return signals
    
    task = Task(
        name="generate_signals",
        task_type=TaskType.SIGNAL,
        func=run,
        interval=3600,  # 每小时
        description="生成多市场交易信号"
    )
    
    scheduler.add_task(task)


def create_trade_task(scheduler: TaskScheduler):
    """创建交易执行任务"""
    
    def run():
        from auto_trade import main as trade_main
        trade_main()
    
    task = Task(
        name="execute_trades",
        task_type=TaskType.TRADE,
        func=run,
        cron_time="09:30",  # 每天9:30
        description="执行交易信号"
    )
    
    scheduler.add_task(task)


def create_report_task(scheduler: TaskScheduler):
    """创建报告任务"""
    
    def run():
        from performance_analyzer import PerformanceAnalyzer
        from data_exporter import DataExporter
        
        # 加载交易数据
        # ... 加载逻辑
        
        # 分析
        # analyzer = PerformanceAnalyzer(trades)
        # report = analyzer.get_report()
        
        # 导出
        # exporter = DataExporter()
        # exporter.export_performance(report)
        
        return "Report generated"
    
    task = Task(
        name="daily_report",
        task_type=TaskType.REPORT,
        func=run,
        cron_time="18:00",  # 每天18:00
        description="生成每日绩效报告"
    )
    
    scheduler.add_task(task)


def create_backup_task(scheduler: TaskScheduler):
    """创建备份任务"""
    
    def run():
        from data_backup import backup_all
        backup_all()
    
    task = Task(
        name="data_backup",
        task_type=TaskType.BACKUP,
        func=run,
        cron_time="02:00",  # 每天2点
        description="每日数据备份"
    )
    
    scheduler.add_task(task)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("定时任务调度器")
    print("=" * 50)
    
    # 创建调度器
    scheduler = TaskScheduler()
    
    # 添加预设任务
    create_signal_task(scheduler)
    create_report_task(scheduler)
    create_backup_task(scheduler)
    
任务
    def    # 添加自定义 my_task():
        print(f"🕐 自定义任务执行: {datetime.now()}")
        return "OK"
    
    scheduler.add_task(Task(
        name="custom_task",
        task_type=TaskType.CHECK,
        func=my_task,
        interval=300,  # 每5分钟
        description="自定义检查任务"
    ))
    
    # 查看任务
    print("\n📋 任务列表:")
    for t in scheduler.get_tasks():
        print(f"  - {t['name']}: {t['description']} ({t['interval']}s)")
    
    # 启动 (只运行一次测试)
    print("\n🚀 启动调度器...")
    scheduler.start()
    
    # 运行一次
    schedule.run_all()
    
    # 状态
    print("\n📊 状态:")
    print(scheduler.get_status())
    
    # 停止
    scheduler.stop()
