#!/usr/bin/env python3
"""
结构化日志系统
支持日志分级、文件输出、日志分析
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogCategory(Enum):
    """日志分类"""
    TRADE = "trade"         # 交易
    SIGNAL = "signal"       # 信号
    RISK = "risk"           # 风控
    DATA = "data"           # 数据
    SYSTEM = "system"       # 系统
    BACKTEST = "backtest"  # 回测


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    category: str
    message: str
    data: Dict = field(default_factory=dict)
    trace_id: Optional[str] = None


class QuantLogger:
    """
    量化日志系统
    
    特性:
    - 结构化日志
    - 分类存储
    - 日志轮转
    - 实时分析
    """
    
    def __init__(self, log_dir: str = "/root/.openclaw/workspace/quant/quant/logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志缓冲 (内存)
        self.buffer: deque = deque(maxlen=1000)
        
        # 文件句柄
        self.files: Dict[str, Any] = {}
        
        # 初始化
        self._init_loggers()
    
    def _init_loggers(self):
        """初始化日志器"""
        # 按分类创建logger
        for category in LogCategory:
            self._create_logger(category.value)
    
    def _create_logger(self, name: str):
        """创建logger"""
        logger = logging.getLogger(f"quant_{name}")
        logger.setLevel(logging.DEBUG)
        
        # 文件 handler
        filepath = os.path.join(self.log_dir, f"{name}.log")
        handler = logging.FileHandler(filepath)
        handler.setLevel(logging.DEBUG)
        
        # 格式
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        # 保存
        self.files[name] = {
            'logger': logger,
            'handler': handler,
            'path': filepath
        }
    
    def log(self, 
            level: LogLevel, 
            category: LogCategory, 
            message: str, 
            data: Optional[Dict] = None,
            trace_id: Optional[str] = None):
        """
        记录日志
        
        Args:
            level: 日志级别
            category: 日志分类
            message: 日志消息
            data: 附加数据
            trace_id: 追踪ID
        """
        # 构建日志条目
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.name,
            category=category.value,
            message=message,
            data=data or {},
            trace_id=trace_id
        )
        
        # 存入缓冲
        self.buffer.append(entry)
        
        # 写入文件
        logger_name = category.value
        if logger_name in self.files:
            logger = self.files[logger_name]['logger']
            
            # 附加数据转字符串
            extra = ""
            if data:
                extra = f" | {json.dumps(data, ensure_ascii=False)}"
            
            log_msg = f"{message}{extra}"
            
            # 根据级别调用
            if level == LogLevel.DEBUG:
                logger.debug(log_msg)
            elif level == LogLevel.INFO:
                logger.info(log_msg)
            elif level == LogLevel.WARNING:
                logger.warning(log_msg)
            elif level == LogLevel.ERROR:
                logger.error(log_msg)
            elif level == LogLevel.CRITICAL:
                logger.critical(log_msg)
    
    def debug(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.DEBUG, category, message, **kwargs)
    
    def info(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.INFO, category, message, **kwargs)
    
    def warning(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.WARNING, category, message, **kwargs)
    
    def error(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.ERROR, category, message, **kwargs)
    
    def critical(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, category, message, **kwargs)
    
    def log_trade(self, action: str, symbol: str, price: float, quantity: float, **kwargs):
        """记录交易"""
        self.info(
            LogCategory.TRADE,
            f"{action} {symbol} x{quantity} @ {price}",
            data={
                'action': action,
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                **kwargs
            }
        )
    
    def log_signal(self, symbol: str, signal: str, confidence: float, **kwargs):
        """记录信号"""
        self.info(
            LogCategory.SIGNAL,
            f"{signal} {symbol} (conf: {confidence:.2%})",
            data={
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                **kwargs
            }
        )
    
    def log_error_with_trace(self, category: LogCategory, message: str, exc: Exception):
        """记录错误及堆栈"""
        self.error(
            category,
            f"{message}: {str(exc)}",
            data={'traceback': traceback.format_exc()}
        )
    
    def get_recent(self, category: LogCategory = None, level: LogLevel = None, n: int = 100) -> list:
        """获取最近N条日志"""
        entries = list(self.buffer)
        
        if category:
            entries = [e for e in entries if e.category == category.value]
        
        if level:
            entries = [e for e in entries if e.level == level.name]
        
        return entries[-n:]
    
    def get_stats(self) -> Dict:
        """获取日志统计"""
        stats = {level.name: 0 for level in LogLevel}
        stats.update({cat.value: 0 for cat in LogCategory})
        
        for entry in self.buffer:
            stats[entry.level] += 1
            stats[entry.category] += 1
        
        return stats
    
    def analyze_errors(self) -> Dict:
        """分析错误"""
        errors = [e for e in self.buffer if e.level in ['ERROR', 'CRITICAL']]
        
        return {
            'total_errors': len(errors),
            'recent_errors': [
                {
                    'time': e.timestamp,
                    'category': e.category,
                    'message': e.message
                }
                for e in errors[-10:]
            ]
        }
    
    def close(self):
        """关闭所有文件"""
        for file_info in self.files.values():
            file_info['handler'].close()


# 全局logger实例
logger = QuantLogger()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("日志系统测试")
    print("=" * 50)
    
    # 记录日志
    logger.info(LogCategory.SYSTEM, "系统启动")
    
    logger.info(LogCategory.TRADE, "买入信号")
    logger.log_trade("BUY", "BTCUSDT", 50000, 0.1)
    
    logger.log_signal("BTCUSDT", "BUY", 0.75)
    
    logger.warning(LogCategory.RISK, "回撤超过5%", data={'drawdown': 0.06})
    
    try:
        1 / 0
    except Exception as e:
        logger.log_error_with_trace(LogCategory.SYSTEM, "计算错误", e)
    
    # 统计
    print("\n📊 日志统计:")
    print(logger.get_stats())
    
    # 错误分析
    print("\n⚠️ 错误分析:")
    print(logger.analyze_errors())
    
    # 关闭
    logger.close()
    print("\n✅ 测试完成")
