"""
市场数据管理模块
- 本地缓存K线数据（带TTL过期）
- 支持多数据源
- 自动更新增量数据
- 错误重试机制
- Binance 合约支持
"""

import os
import json
import time
import ccxt
import baostock as bs
import pandas as pd
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "market")
CACHE_TTL = {  # 缓存过期时间（秒）
    '1m': 60,      # 1分钟K线缓存1分钟
    '5m': 300,     # 5分钟K线缓存5分钟
    '15m': 900,    # 15分钟K线缓存15分钟
    '1h': 1800,    # 1小时K线缓存30分钟
    '4h': 3600,    # 4小时K线缓存1小时
    '1d': 14400,   # 日K线缓存4小时
}
RETRY_CONFIG = {
    'max_retries': 3,
    'retry_delay': 1,  # 秒
    'backoff': 2,  # 指数退避
}

os.makedirs(DATA_DIR, exist_ok=True)


# ==================== 错误重试装饰器 ====================
def retry_on_error(max_retries: int = 3, delay: float = 1, backoff: float = 2):
    """错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"{func.__name__} 失败，{wait_time:.1f}秒后重试 ({attempt+1}/{max_retries}): {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} 失败次数过多: {e}")
            raise last_exception
        return wrapper
    return decorator


# ==================== 统一数据格式 ====================
"""
标准K线数据格式:
{
    "timestamp": 1234567890000,  # 毫秒时间戳
    "datetime": "2024-01-01T00:00:00",  # ISO格式
    "open": 50000.0,
    "high": 51000.0,
    "low": 49000.0,
    "close": 50500.0,
    "volume": 1000.0
}
"""


def normalize_kline(data, source='unknown'):
    """
    统一数据格式
    
    Args:
        data: 原始数据 (dict, list, DataFrame)
        source: 数据源 (ccxt, baostock, yfinance, tushare)
    
    Returns:
        list: 标准格式K线数据
    """
    if data is None:
        return []
    
    # 如果已经是标准格式
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict) and 'timestamp' in data[0]:
            return data
    
    # 转换为DataFrame处理
    if isinstance(data, pd.DataFrame):
        df = data
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        return []
    
    result = []
    
    for _, row in df.iterrows():
        try:
            kline = {}
            
            # 时间戳
            if 'timestamp' in df.columns:
                kline['timestamp'] = int(row['timestamp'])
            elif 'datetime' in df.columns:
                dt = pd.to_datetime(row['datetime'])
                kline['timestamp'] = int(dt.timestamp() * 1000)
            elif 'date' in df.columns:
                dt = pd.to_datetime(row['date'])
                kline['timestamp'] = int(dt.timestamp() * 1000)
            else:
                continue
            
            # 格式化时间
            kline['datetime'] = datetime.fromtimestamp(
                kline['timestamp'] / 1000
            ).isoformat()
            
            # 价格
            kline['open'] = float(row.get('open', row.get('Open', 0)))
            kline['high'] = float(row.get('high', row.get('High', 0)))
            kline['low'] = float(row.get('low', row.get('Low', 0)))
            kline['close'] = float(row.get('close', row.get('Close', 0)))
            
            # 成交量
            kline['volume'] = float(row.get('volume', row.get('Volume', 0)))
            
            # 标记数据源
            kline['source'] = source
            
            result.append(kline)
            
        except (ValueError, TypeError, KeyError):
            continue
    
    return result


class MarketDataManager:
    """市场数据管理器 - 带缓存和重试"""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,  # 启用限流
            'options': {'defaultType': 'spot'}  # 默认现货
        })
    
    def _get_cache_path(self, symbol, timeframe):
        """获取缓存文件路径"""
        filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
        return os.path.join(DATA_DIR, filename)
    
    def _load_cache(self, symbol, timeframe):
        """加载缓存数据（带TTL检查，兼容旧格式）"""
        path = self._get_cache_path(symbol, timeframe)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # 兼容旧格式（直接是列表）
                if isinstance(data, list):
                    return data
                
                # 新格式带TTL
                cache_time = data.get('_cache_time', 0)
                ttl = CACHE_TTL.get(timeframe, 3600)
                if time.time() - cache_time > ttl:
                    logger.debug(f"缓存已过期: {symbol} {timeframe}")
                    return None
                return data.get('data')
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
                return None
        return None
    
    def _save_cache(self, symbol, timeframe, data):
        """保存缓存数据（带时间戳）"""
        path = self._get_cache_path(symbol, timeframe)
        cache_data = {
            '_cache_time': time.time(),
            '_symbol': symbol,
            '_timeframe': timeframe,
            'data': data
        }
        with open(path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def _fetch_ohlcv(self, symbol, timeframe, since=None, limit=500):
        """获取K线数据（带重试）"""
        try:
            if since:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            else:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except ccxt.NetworkError as e:
            logger.warning(f"网络错误，重试中: {e}")
            # 尝试重新连接
            self.exchange = ccxt.binance({'enableRateLimit': True})
            raise
        except ccxt.RateLimitExceeded as e:
            logger.warning(f"触发限流，等待后重试: {e}")
            time.sleep(5)
            raise
    
    def get_btc_klines(self, timeframe='1h', since=None, limit=500, use_cache=True):
        """
        获取BTC K线数据
        
        Args:
            timeframe: 时间周期 (1m, 5m, 15m, 1h, 4h, 1d)
            since: 开始时间戳 (毫秒)
            limit: 获取数量
            use_cache: 是否使用缓存
        
        Returns:
            list: K线数据 [{timestamp, open, high, low, close, volume}]
        """
        symbol = 'BTC/USDT'
        cache = self._load_cache(symbol, timeframe) if use_cache else None
        
        if cache and since is None:
            # 使用缓存，获取最新数据
            last_ts = cache[-1]['timestamp'] if cache else 0
            since = last_ts + 1
        
        # 获取新数据（使用带重试的方法）
        try:
            ohlcv = self._fetch_ohlcv(symbol, timeframe, since, limit)
            
            if not ohlcv:
                return cache if cache else []
            
            # 转换为标准格式
            data = [
                {
                    'timestamp': k[0],
                    'datetime': datetime.fromtimestamp(k[0]/1000).isoformat(),
                    'open': k[1],
                    'high': k[2],
                    'low': k[3],
                    'close': k[4],
                    'volume': k[5]
                }
                for k in ohlcv
            ]
            
            # 合并缓存
            if cache and since:
                # 去重合并
                existing_ts = set(c['timestamp'] for c in cache)
                new_data = [d for d in data if d['timestamp'] not in existing_ts]
                data = cache + new_data
                data.sort(key=lambda x: x['timestamp'])
            
            # 保存缓存
            if use_cache:
                self._save_cache(symbol, timeframe, data)
            
            return data
            
        except Exception as e:
            print(f"获取BTC数据失败: {e}")
            return cache if cache else []
    
    def get_a_stock_klines(self, code, start_date, end_date):
        """
        获取A股K线数据
        
        Args:
            code: 股票代码 (sh.000300, sz.399001)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame: K线数据
        """
        bs.login()
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=start_date, end_date=end_date, frequency="d"
        )
        
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
        bs.logout()
        
        if not data_list:
            return []
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        return normalize_kline(df, 'baostock')
    
    def get_a_stock_tushare(self, ts_code, start_date, end_date):
        """
        使用Tushare获取A股数据
        
        Args:
            ts_code: Tushare股票代码 (000300.SZ, 600519.SH)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: K线数据
        """
        try:
            import tushare as ts
            # 需要设置token，请在config中配置
            # ts.set_token('YOUR_TOKEN')
            # pro = ts.pro_api()
            
            # 使用免费接口
            df = ts.get_k_data(ts_code, start=start_date.replace('-', ''), 
                               end=end_date.replace('-', ''))
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={'date': 'datetime', 'close': 'close'})
            return normalize_kline(df, 'tushare')
            
        except ImportError:
            print("Tushare未安装，请运行: pip install tushare")
            return []
        except Exception as e:
            print(f"Tushare获取数据失败: {e}")
            return []
    
    def get_a_stock_akshare(self, symbol, start_date, end_date):
        """
        使用AKShare获取A股数据
        """
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            if df is None or df.empty:
                return []
            # 重命名列
            df = df.rename(columns={
                '日期': 'datetime', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            return df
        except Exception as e:
            print(f"AKShare获取失败: {e}")
            return []
    
    def get_us_stock_klines(self, symbol, start_date, end_date):
        """
        获取美股K线数据
        
        Args:
            symbol: 股票代码 (SPY, AAPL)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame: K线数据
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return []
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            return normalize_kline(df, 'yfinance')
        except Exception as e:
            print(f"获取美股数据失败: {e}")
            return []
    
    def get_akshare_data(self, symbol, start_date, end_date, adjust=""):
        """
        使用AKShare获取A股数据
        
        Args:
            symbol: 股票代码 (sh000300, sz000001)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权类型 ("qfq", "hfq", "")
        
        Returns:
            DataFrame: K线数据
        """
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, 
                                    end_date=end_date, adjust=adjust)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            return df
        except ImportError:
            print("AKShare未安装")
            return pd.DataFrame()
        except Exception as e:
            print(f"AKShare获取失败: {e}")
            return pd.DataFrame()
    
    def get_market_data(self, market, symbol, **kwargs):
        """
        统一获取市场数据接口
        
        Args:
            market: 市场 (BTC/A股/美股)
            symbol: 交易对/代码
            **kwargs: 其他参数
        
        Returns:
            格式因市场不同而异
        """
        if market == 'BTC':
            return self.get_btc_klines(**kwargs)
        elif market == 'A股':
            return self.get_a_stock_klines(symbol, **kwargs)
        elif market == '美股':
            return self.get_us_stock_klines(symbol, **kwargs)
        else:
            raise ValueError(f"不支持的市场: {market}")


# 全局实例
_data_manager = None
_futures_manager = None


class FuturesDataManager:
    """Binance 合约数据管理器"""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # 合约
        })
        self.usdt_exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future', 'defaultMarginMode': 'cross'}
        })
    
    def _get_cache_path(self, symbol, timeframe):
        """获取缓存文件路径"""
        filename = f"futures_{symbol.replace('/', '_')}_{timeframe}.json"
        return os.path.join(DATA_DIR, filename)
    
    def _load_cache(self, symbol, timeframe):
        """加载缓存数据（带TTL检查）"""
        path = self._get_cache_path(symbol, timeframe)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                cache_time = data.get('_cache_time', 0)
                ttl = CACHE_TTL.get(timeframe, 1800)
                if time.time() - cache_time > ttl:
                    return None
                return data.get('data')
            except:
                return None
        return None
    
    def _save_cache(self, symbol, timeframe, data):
        """保存缓存数据"""
        path = self._get_cache_path(symbol, timeframe)
        cache_data = {
            '_cache_time': time.time(),
            '_symbol': symbol,
            '_timeframe': timeframe,
            'data': data
        }
        with open(path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def _fetch_ohlcv(self, symbol, timeframe, since=None, limit=500):
        """获取合约K线数据"""
        try:
            if since:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            else:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except ccxt.RateLimitExceeded:
            logger.warning("触发限流，等待5秒")
            time.sleep(5)
            raise
    
    def get_futures_klines(self, symbol='BTC/USDT:USDT', timeframe='1h', since=None, limit=500, use_cache=True):
        """
        获取合约K线数据
        
        Args:
            symbol: 合约符号 (BTC/USDT:USDT 表示BTC永续合约)
            timeframe: 时间周期
            since: 开始时间戳 (毫秒)
            limit: 获取数量
            use_cache: 是否使用缓存
        
        Returns:
            list: K线数据
        """
        cache = self._load_cache(symbol, timeframe) if use_cache else None
        
        if cache and since is None:
            last_ts = cache[-1]['timestamp'] if cache else 0
            since = last_ts + 1
        
        try:
            ohlcv = self._fetch_ohlcv(symbol, timeframe, since, limit)
            
            if not ohlcv:
                return cache if cache else []
            
            data = [
                {
                    'timestamp': k[0],
                    'datetime': datetime.fromtimestamp(k[0]/1000).isoformat(),
                    'open': k[1],
                    'high': k[2],
                    'low': k[3],
                    'close': k[4],
                    'volume': k[5]
                }
                for k in ohlcv
            ]
            
            if cache and since:
                existing_ts = set(c['timestamp'] for c in cache)
                new_data = [d for d in data if d['timestamp'] not in existing_ts]
                data = cache + new_data
                data.sort(key=lambda x: x['timestamp'])
            
            if use_cache:
                self._save_cache(symbol, timeframe, data)
            
            return data
            
        except Exception as e:
            logger.error(f"获取合约数据失败: {e}")
            return cache if cache else []
    
    def get_ticker(self, symbol='BTC/USDT:USDT'):
        """获取合约最新行情"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume24h': ticker['baseVolume'],
                'priceChange24h': ticker['percentage'],
                'high24h': ticker['high'],
                'low24h': ticker['low'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return None
    
    def get_funding_rate(self, symbol='BTC/USDT:USDT'):
        """获取合约资金费率"""
        try:
            # 使用 Binance API 直接获取
            import requests
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            params = {'symbol': 'BTCUSDT'}
            resp = requests.get(url, params=params, timeout=10).json()
            return {
                'symbol': symbol,
                'markPrice': float(resp.get('markPrice', 0)),
                'indexPrice': float(resp.get('indexPrice', 0)),
                'lastFundingRate': float(resp.get('lastFundingRate', 0)),
                'nextFundingTime': resp.get('nextFundingTime')
            }
        except Exception as e:
            logger.error(f"获取资金费率失败: {e}")
            return None
    
    def get_open_interest(self, symbol='BTC/USDT:USDT'):
        """获取合约持仓量"""
        try:
            import requests
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            params = {'symbol': 'BTCUSDT'}
            resp = requests.get(url, params=params, timeout=10).json()
            return {
                'symbol': symbol,
                'openInterest': float(resp.get('openInterest', 0)),
                'timestamp': resp.get('timestamp')
            }
        except Exception as e:
            logger.error(f"获取持仓量失败: {e}")
            return None


def get_data_manager():
    """获取现货数据管理器实例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = MarketDataManager()
    return _data_manager


def get_futures_manager():
    """获取合约数据管理器实例"""
    global _futures_manager
    if _futures_manager is None:
        _futures_manager = FuturesDataManager()
    return _futures_manager


if __name__ == '__main__':
    # 测试
    dm = get_data_manager()
    
    # 测试BTC数据
    print("获取BTC数据...")
    data = dm.get_btc_klines('1h', limit=100)
    print(f"获取到 {len(data)} 条数据")
    if data:
        print(f"最新: {data[-1]['datetime']} close: {data[-1]['close']}")
