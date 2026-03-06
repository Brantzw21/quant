"""
异步数据获取模块
- 并行获取多个交易对
- 批量更新市场数据
"""

import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import json


class AsyncDataFetcher:
    """异步数据获取器"""
    
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def fetch_multiple(self, fetch_func, symbols):
        """
        并行获取多个交易对数据
        
        Args:
            fetch_func: 获取数据的函数
            symbols: 交易对列表
        
        Returns:
            dict: {symbol: data}
        """
        import pandas as pd
        
        results = {}
        
        # 使用线程池并行获取
        futures = {}
        for symbol in symbols:
            future = self.executor.submit(fetch_func, symbol)
            futures[future] = symbol
        
        for future in futures:
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
                results[symbol] = None
        
        return results
    
    def batch_update_pool(self, pool_config, fetch_func):
        """
        批量更新池中所有交易对
        
        Args:
            pool_config: 池配置
            fetch_func: 获取函数 (symbol) -> data
        
        Returns:
            dict: 更新结果
        """
        # 获取启用的交易对
        enabled = []
        for market, symbols in pool_config.get('pools', {}).items():
            for s in symbols:
                if s.get('enabled', False):
                    enabled.append({
                        'market': market,
                        'symbol': s['symbol'],
                        'name': s.get('name', s['symbol'])
                    })
        
        print(f"并行获取 {len(enabled)} 个交易对...")
        
        # 并行获取
        results = self.fetch_multiple(fetch_func, [s['symbol'] for s in enabled])
        
        # 汇总结果
        success = sum(1 for v in results.values() if v is not None)
        print(f"成功: {success}/{len(enabled)}")
        
        return results
    
    def close(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)


# 便捷函数
def parallel_fetch(fetch_dict, max_workers=5):
    """
    并行获取多个数据源
    
    Args:
        fetch_dict: {name: fetch_func}
    
    Returns:
        dict: {name: data}
    """
    fetcher = AsyncDataFetcher(max_workers)
    results = fetcher.fetch_multiple(lambda x: x, list(fetch_dict.values()))
    fetcher.close()
    return results


if __name__ == '__main__':
    # 测试
    from data_manager import get_data_manager
    
    dm = get_data_manager()
    
    # 需要先实现获取函数
    print("使用: fetcher.batch_update_pool(pool_config, fetch_func)")
