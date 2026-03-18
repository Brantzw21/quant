#!/usr/bin/env python3
"""
统一数据预处理 Pipeline
标准化数据获取、清洗、指标计算

Features:
- 多数据源支持 (Binance, Baostock, etc.)
- 数据验证与清洗
- 指标批量计算
- 时间序列对齐
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class DataConfig:
    """数据配置"""
    # 必需列
    required_columns: List[str] = None
    
    # 填充策略
    fill_method: str = 'ffill'  # ffill, bfill, interpolate
    min_rows: int = 100         # 最小数据量
    
    # 指标计算
    indicators: List[str] = None  # 需要计算的指标列表
    
    # 频率对齐
    target_freq: Optional[str] = None  # 4h, 1h, 1d, etc.


# 默认指标配置
DEFAULT_INDICATORS = {
    'sma': [7, 25, 99],
    'ema': [12, 26],
    'rsi': [14],
    'macd': [12, 26, 9],
    'bb': [20, 2],
    'atr': [14],
    'adx': [14],
    'volume_sma': [20],
}


class DataPipeline:
    """
    统一数据预处理 Pipeline
    
    用法:
        pipeline = DataPipeline()
        df = pipeline.process(raw_data)
        df = pipeline.add_indicators(df, ['rsi', 'macd'])
    """
    
    def __init__(self, config: DataConfig = None):
        self.config = config or DataConfig()
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if self.config.required_columns is None:
            self.config.required_columns = ['close']
        if self.config.indicators is None:
            self.config.indicators = []
    
    def process(self, df: pd.DataFrame, 
                required_columns: List[str] = None,
                min_rows: int = None) -> pd.DataFrame:
        """
        完整处理流程
        
        1. 列名标准化
        2. 必需列检查
        3. 数据清洗
        4. 时间索引处理
        5. 数据验证
        """
        df = df.copy()
        required = required_columns or self.config.required_columns
        min_rows = min_rows or self.config.min_rows
        
        # 1. 列名标准化 (统一为小写)
        df.columns = df.columns.str.lower()
        
        # 2. 必需列检查
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")
        
        # 3. 时间索引处理
        df = self._process_index(df)
        
        # 4. 数据清洗
        df = self._clean_data(df)
        
        # 5. 数据验证
        if len(df) < min_rows:
            raise ValueError(f"数据量不足: {len(df)} < {min_rows}")
        
        # 6. 填充可选列
        df = self._fill_optional_columns(df)
        
        # 7. 排序
        df = df.sort_index()
        
        return df
    
    def _process_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理时间索引"""
        # 如果没有索引，生成虚拟索引
        if df.index is None or len(df) == 0:
            df.index = pd.RangeIndex(len(df))
        
        # 尝试将第一列转为时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            for col in df.columns:
                if 'time' in col.lower() or 'date' in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col])
                        df = df.set_index(col)
                        break
                    except:
                        pass
        
        # 确保索引可排序
        try:
            df = df.sort_index()
        except:
            pass
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗数据"""
        # 删除全空行
        df = df.dropna(how='all')
        
        # 删除重复索引
        df = df[~df.index.duplicated(keep='first')]
        
        # 数值列：替换 inf 和 大NaN
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
        
        return df
    
    def _fill_optional_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """填充可选列"""
        # OHLCV 填充
        if 'close' in df.columns:
            if 'open' not in df.columns:
                df['open'] = df['close']
            if 'high' not in df.columns:
                df['high'] = df[['open', 'close']].max(axis=1)
            if 'low' not in df.columns:
                df['low'] = df[['open', 'close']].min(axis=1)
            if 'volume' not in df.columns:
                df['volume'] = 0
        
        # 填充缺失值
        method = self.config.fill_method
        if method == 'ffill':
            df = df.ffill()
        elif method == 'bfill':
            df = df.bfill()
        elif method == 'interpolate':
            df = df.interpolate(method='linear')
        
        # 再次处理剩余 NaN
        df = df.fillna(0)
        
        return df
    
    def add_indicators(self, df: pd.DataFrame, 
                       indicators: List[str] = None,
                       params: Dict = None) -> pd.DataFrame:
        """
        添加技术指标
        
        Args:
            df: 输入数据
            indicators: 指标列表 ['sma', 'ema', 'rsi', 'macd', 'bb', 'atr', 'adx']
            params: 指标参数覆盖
        """
        df = df.copy()
        indicators = indicators or self.config.indicators or []
        params = params or {}
        
        for name in indicators:
            config = params.get(name, DEFAULT_INDICATORS.get(name, [14]))
            
            if name == 'sma':
                df = self._add_sma(df, config if isinstance(config, list) else [config])
            elif name == 'ema':
                df = self._add_ema(df, config if isinstance(config, list) else [config])
            elif name == 'rsi':
                df = self._add_rsi(df, config[0] if isinstance(config, list) else config)
            elif name == 'macd':
                df = self._add_macd(df, *config[:3] if isinstance(config, (list, tuple)) else (12, 26, 9))
            elif name == 'bb':
                df = self._add_bollinger(df, *config[:2] if isinstance(config, (list, tuple)) else (20, 2))
            elif name == 'atr':
                df = self._add_atr(df, config[0] if isinstance(config, list) else config)
            elif name == 'adx':
                df = self._add_adx(df, config[0] if isinstance(config, list) else config)
            elif name == 'volume_sma':
                df = self._add_volume_sma(df, config[0] if isinstance(config, list) else config)
        
        return df
    
    def _add_sma(self, df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """简单移动平均"""
        close = df['close']
        for p in periods:
            df[f'sma_{p}'] = close.rolling(p).mean()
        return df
    
    def _add_ema(self, df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """指数移动平均"""
        close = df['close']
        for p in periods:
            df[f'ema_{p}'] = close.ewm(span=p, adjust=False).mean()
        return df
    
    def _add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 指标"""
        close = df['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    def _add_macd(self, df: pd.DataFrame, 
                  fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD 指标"""
        close = df['close']
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df
    
    def _add_bollinger(self, df: pd.DataFrame, 
                       period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """布林带"""
        close = df['close']
        sma = close.rolling(period).mean()
        std = close.rolling(period).std()
        
        df['bb_middle'] = sma
        df['bb_upper'] = sma + std * std_dev
        df['bb_lower'] = sma - std * std_dev
        return df
    
    def _add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ATR 真实波动幅度"""
        high = df.get('high', df['close'])
        low = df.get('low', df['close'])
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        df['atr'] = tr.rolling(period).mean()
        df['atr_pct'] = df['atr'] / df['close'] * 100  # ATR 百分比
        return df
    
    def _add_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ADX 趋向指标"""
        high = df.get('high', df['close'])
        low = df.get('low', df['close'])
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = self._true_range(high, low, close)
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr)
        
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        df['adx'] = dx.rolling(period).mean()
        df['adx_plus'] = plus_di
        df['adx_minus'] = minus_di
        
        return df
    
    def _true_range(self, high, low, close) -> pd.Series:
        """计算真实波动幅度"""
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    def _add_volume_sma(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """成交量均线"""
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(period).mean()
        return df
    
    def align_frequency(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """频率对齐 (重采样)"""
        if not isinstance(df.index, pd.DatetimeIndex):
            return df
        
        # 成交量用 sum，其他用 last
        agg_rules = {
            'open': 'last',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # 只保留存在的列
        agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
        
        return df.resample(freq).agg(agg_rules).dropna()
    
    def validate_ohlcv(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证 OHLCV 数据质量
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # 检查必需列
        required = ['open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                errors.append(f"缺少列: {col}")
        
        if errors:
            return False, errors
        
        # 检查价格关系: high >= low, high >= open/close, low <= open/close
        invalid_high = (df['high'] < df['low']).sum()
        if invalid_high > 0:
            errors.append(f"high < low: {invalid_high} 行")
        
        invalid_ohlc = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()
        if invalid_ohlc > 0:
            errors.append(f"high < open/close: {invalid_ohlc} 行")
        
        invalid_olc = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()
        if invalid_olc > 0:
            errors.append(f"low > open/close: {invalid_olc} 行")
        
        # 检查负值
        for col in ['open', 'high', 'low', 'close']:
            if (df[col] <= 0).sum() > 0:
                errors.append(f"{col} 存在非正值")
        
        # 检查成交量
        if 'volume' in df.columns and (df['volume'] < 0).sum() > 0:
            errors.append("volume 存在负值")
        
        return len(errors) == 0, errors


# 便捷函数
def prepare_data(df: pd.DataFrame, 
                 indicators: List[str] = None,
                 validate: bool = True) -> pd.DataFrame:
    """
    便捷数据预处理函数
    
    Args:
        df: 原始数据
        indicators: 需要添加的指标
        validate: 是否验证数据质量
    """
    pipeline = DataPipeline()
    
    # 处理
    df = pipeline.process(df)
    
    # 验证
    if validate:
        is_valid, errors = pipeline.validate_ohlcv(df)
        if not is_valid:
            print(f"⚠️ 数据验证警告: {errors}")
    
    # 添加指标
    if indicators:
        df = pipeline.add_indicators(df, indicators)
    
    return df


__all__ = [
    'DataConfig',
    'DataPipeline',
    'prepare_data',
    'DEFAULT_INDICATORS',
]
