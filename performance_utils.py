#!/usr/bin/env python3
"""
性能优化工具
缓存、数据加载优化、并行计算
"""

import os
import sys
import time
import json
import hashlib
import pickle
from typing import Any, Callable, Dict
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class DataCache:
    """
    数据缓存
    
    功能:
    - 内存缓存
    - 文件缓存
    - 过期清理
    """
    
    def __init__(self, cache_dir: str = "/root/.openclaw/workspace/quant/quant/data/cache"):
        self.cache_dir = cache_dir
        self.memory_cache: Dict = {}
        self.max_memory_items = 100
        
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_key_hash(self, key: str) -> str:
        """生成key的hash"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str, max_age: int = 3600) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存key
            max_age: 最大年龄(秒)
        
        Returns:
            缓存值，如果不存在或过期返回None
        """
        # 内存缓存
        if key in self.memory_cache:
            cached = self.memory_cache[key]
            if time.time() - cached['timestamp'] < max_age:
                return cached['value']
            else:
                del self.memory_cache[key]
        
        # 文件缓存
        file_key = self._get_key_hash(key)
        filepath = os.path.join(self.cache_dir, f"{file_key}.cache")
        
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            
            if time.time() - mtime < max_age:
                try:
                    with open(filepath, 'rb') as f:
                        return pickle.load(f)
                except:
                    pass
        
        return None
    
    def set(self, key: str, value: Any, to_file: bool = True):
        """
        设置缓存
        
        Args:
            key: 缓存key
            value: 缓存值
            to_file: 是否持久化到文件
        """
        # 内存缓存
        self.memory_cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        
        # 限制内存缓存大小
        if len(self.memory_cache) > self.max_memory_items:
            oldest = min(self.memory_cache.items(), 
                       key=lambda x: x[1]['timestamp'])
            del self.memory_cache[oldest[0]]
        
        # 文件缓存
        if to_file:
            file_key = self._get_key_hash(key)
            filepath = os.path.join(self.cache_dir, f"{file_key}.cache")
            
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump(value, f)
            except:
                pass
    
    def clear(self, older_than: int = None):
        """
        清理缓存
        
        Args:
            older_than: 清理 older_than 秒之前的缓存
        """
        # 内存缓存
        if older_than:
            now = time.time()
            keys_to_delete = [
                k for k, v in self.memory_cache.items()
                if now - v['timestamp'] > older_than
            ]
            for k in keys_to_delete:
                del self.memory_cache[k]
        else:
            self.memory_cache.clear()
        
        # 文件缓存
        if os.path.exists(self.cache_dir):
            for f in os.listdir(self.cache_dir):
                if f.endswith('.cache'):
                    filepath = os.path.join(self.cache_dir, f)
                    
                    if older_than:
                        mtime = os.path.getmtime(filepath)
                        if time.time() - mtime > older_than:
                            os.remove(filepath)
                    else:
                        os.remove(filepath)


class DataLoader:
    """
    数据加载器
    
    功能:
    - 批量加载
    - 并行加载
    - 自动缓存
    """
    
    def __init__(self, use_cache: bool = True):
        self.cache = DataCache() if use_cache else None
    
    def load_csv(self, filepath: str, use_cache: bool = True) -> pd.DataFrame:
        """加载CSV"""
        # 尝试缓存
        if use_cache and self.cache:
            cached = self.cache.get(f"csv:{filepath}")
            if cached is not None:
                return cached
        
        # 加载
        df = pd.read_csv(filepath)
        
        # 缓存
        if use_cache and self.cache:
            self.cache.set(f"csv:{filepath}", df)
        
        return df
    
    def load_multiple(self, files: list, parallel: bool = False) -> Dict[str, pd.DataFrame]:
        """批量加载"""
        if parallel:
            return self._load_parallel(files)
        else:
            return self._load_sequential(files)
    
    def _load_sequential(self, files: list) -> Dict[str, pd.DataFrame]:
        """顺序加载"""
        results = {}
        
        for f in files:
            name = os.path.basename(f).replace('.csv', '')
            results[name] = self.load_csv(f)
        
        return results
    
    def _load_parallel(self, files: list) -> Dict[str, pd.DataFrame]:
        """并行加载"""
        from concurrent.futures import ThreadPoolExecutor
        
        results = {}
        
        def load_file(f):
            name = os.path.basename(f).replace('.csv', '')
            return name, self.load_csv(f)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            for name, df in executor.map(load_file, files):
                results[name] = df
        
        return results


def timed_cache(max_age: int = 60):
    """
    计时缓存装饰器
    
    Args:
        max_age: 缓存时间(秒)
    """
    def decorator(func: Callable):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成cache key
            key = str(args) + str(kwargs)
            key_hash = hashlib.md5(key.encode()).hexdigest()
            
            now = time.time()
            
            # 检查缓存
            if key_hash in cache:
                cached_time, cached_value = cache[key_hash]
                if now - cached_time < max_age:
                    return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 保存缓存
            cache[key_hash] = (now, result)
            
            return result
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """
    性能监控
    
    功能:
    - 执行时间统计
    - 内存使用
    - 函数调用统计
    """
    
    def __init__(self):
        self.stats = {}
    
    def measure(self, func: Callable, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        elapsed = time.time() - start_time
        
        # 统计
        func_name = func.__name__
        
        if func_name not in self.stats:
            self.stats[func_name] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        stats = self.stats[func_name]
        stats['count'] += 1
        stats['total_time'] += elapsed
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], elapsed)
        stats['max_time'] = max(stats['max_time'], elapsed)
        
        return result, elapsed
    
    def get_stats(self) -> pd.DataFrame:
        """获取性能统计"""
        if not self.stats:
            return pd.DataFrame()
        
        data = []
        
        for name, s in self.stats.items():
            data.append({
                'function': name,
                'calls': s['count'],
                'total_time': round(s['total_time'], 3),
                'avg_time': round(s['avg_time'], 4),
                'min_time': round(s['min_time'], 4),
                'max_time': round(s['max_time'], 4)
            })
        
        return pd.DataFrame(data).sort_values('total_time', ascending=False)
    
    def print_stats(self):
        """打印性能统计"""
        df = self.get_stats()
        
        if df.empty:
            print("无性能数据")
            return
        
        print("\n📊 性能统计:")
        print(df.to_string(index=False))


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("性能优化工具")
    print("=" * 50)
    
    # 测试缓存
    cache = DataCache()
    
    print("\n📦 测试缓存:")
    cache.set("test_key", {"data": [1, 2, 3]})
    result = cache.get("test_key")
    print(f"  缓存读取: {result}")
    
    # 测试计时装饰器
    @timed_cache(max_age=5)
    def slow_function(n):
        time.sleep(0.1)
        return n * 2
    
    print("\n⏱️ 测试计时缓存:")
    import time
    start = time.time()
    slow_function(5)
    print(f"  首次调用: {time.time() - start:.3f}s")
    
    start = time.time()
    slow_function(5)
    print(f"  缓存调用: {time.time() - start:.3f}s")
    
    # 性能监控
    monitor = PerformanceMonitor()
    
    def dummy_func():
        time.sleep(0.01)
        return 1
    
    for _ in range(10):
        monitor.measure(dummy_func)
    
    monitor.print_stats()
