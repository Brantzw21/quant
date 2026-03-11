#!/usr/bin/env python3
"""
流动性分析器
分析资产流动性、市场深度
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class LiquidityMetrics:
    """流动性指标"""
    daily_volume: float      # 日成交量
    volume_score: float     # 成交量得分 0-100
    spread: float           # 买卖价差
    spread_score: float     # 价差得分 0-100
    depth: float            # 市场深度
    depth_score: float      # 深度得分 0-100
    slippage_estimate: float # 预估滑点
    liquidity_rating: str    # 流动性评级 A/B/C/D


class LiquidityAnalyzer:
    """
    流动性分析器
    
    分析维度:
    - 成交量
    - 价差
    - 市场深度
    - 滑点估算
    """
    
    def __init__(self):
        # 流动性阈值配置
        self.volume_thresholds = {
            'A': 1_000_000_000,  # >10亿
            'B': 100_000_000,    # >1亿
            'C': 10_000_000,     # >1000万
            'D': 0
        }
        
        self.spread_thresholds = {
            'A': 0.0005,   # <0.05%
            'B': 0.001,    # <0.1%
            'C': 0.005,     # <0.5%
            'D': 1.0
        }
    
    def analyze(self, symbol: str, market: str = 'binance') -> LiquidityMetrics:
        """
        分析流动性
        """
        if market == 'binance':
            return self._analyze_binance(symbol)
        elif market == 'stock':
            return self._analyze_stock(symbol)
        else:
            return self._analyze_generic(symbol)
    
    def _analyze_binance(self, symbol: str) -> LiquidityMetrics:
        """分析Binance合约流动性"""
        try:
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 1. 获取24h统计
            stats = client.get_ticker(symbol=symbol)
            
            daily_volume = float(stats['volume'])
            quote_volume = float(stats['quoteVolume'])
            last_price = float(stats['lastPrice'])
            
            # 2. 获取订单簿
            depth = client.get_order_book(symbol=symbol, limit=20)
            
            bids = np.array([float(b[1]) for b in depth['bids']])
            asks = np.array([float(a[1]) for a in depth['asks']])
            
            best_bid = float(depth['bids'][0][0])
            best_ask = float(depth['asks'][0][0])
            
            # 计算价差
            spread = (best_ask - best_bid) / best_bid
            
            # 计算深度
            depth_value = (np.sum(bids) * best_bid + np.sum(asks) * best_ask)
            
            # 计算滑点 (基于订单簿)
            slippage = self._estimate_slippage(best_bid, bids, 10000)  # 假设交易1万
            
            # 评分
            volume_score = self._score_volume(quote_volume)
            spread_score = self._score_spread(spread)
            depth_score = self._score_depth(depth_value)
            
            # 综合评级
            rating = self._calculate_rating(volume_score, spread_score, depth_score)
            
            return LiquidityMetrics(
                daily_volume=quote_volume,
                volume_score=volume_score,
                spread=spread,
                spread_score=spread_score,
                depth=depth_value,
                depth_score=depth_score,
                slippage_estimate=slippage,
                liquidity_rating=rating
            )
            
        except Exception as e:
            print(f"分析失败: {e}")
            return self._default_metrics()
    
    def _analyze_stock(self, symbol: str) -> LiquidityMetrics:
        """分析股票流动性"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            daily_volume = info.get('volume', 0) or 0
            last_price = info.get('currentPrice', 0) or 0
            
            # 股票通常没有订单簿数据，用成交量估算
            quote_volume = daily_volume * last_price
            
            # 假设价差0.1%
            spread = 0.001
            
            # 估算深度
            depth_value = quote_volume * 0.1
            
            # 评分
            volume_score = self._score_volume(quote_volume)
            spread_score = self._score_spread(spread)
            depth_score = self._score_depth(depth_value)
            
            # 滑点估算
            slippage = spread * 0.5
            
            # 评级
            rating = self._calculate_rating(volume_score, spread_score, depth_score)
            
            return LiquidityMetrics(
                daily_volume=quote_volume,
                volume_score=volume_score,
                spread=spread,
                spread_score=spread_score,
                depth=depth_value,
                depth_score=depth_score,
                slippage_estimate=slippage,
                liquidity_rating=rating
            )
            
        except Exception as e:
            print(f"分析失败: {e}")
            return self._default_metrics()
    
    def _analyze_generic(self, symbol: str) -> LiquidityMetrics:
        """通用分析"""
        return self._default_metrics()
    
    def _estimate_slippage(self, price: float, volumes: np.ndarray, trade_value: float) -> float:
        """
        估算滑点
        
        基于订单簿深度计算给定交易额的滑点
        """
        # 简化计算
        # 假设订单簿均匀分布
        
        avg_volume = np.mean(volumes) if len(volumes) > 0 else 0
        
        if avg_volume == 0:
            return 0.01  # 1%
        
        # 交易量占订单簿的比例
        volume_ratio = trade_value / (avg_volume * len(volumes) * price)
        
        # 简化滑点模型
        slippage = min(volume_ratio * 0.01, 0.1)  # 最多10%
        
        return slippage
    
    def _score_volume(self, volume: float) -> float:
        """成交量评分"""
        if volume > self.volume_thresholds['A']:
            return 100
        elif volume > self.volume_thresholds['B']:
            return 80
        elif volume > self.volume_thresholds['C']:
            return 60
        else:
            return 40
    
    def _score_spread(self, spread: float) -> float:
        """价差评分"""
        if spread < self.spread_thresholds['A']:
            return 100
        elif spread < self.spread_thresholds['B']:
            return 80
        elif spread < self.spread_thresholds['C']:
            return 60
        else:
            return 40
    
    def _score_depth(self, depth: float) -> float:
        """深度评分"""
        # 以10万为基准
        if depth > 1_000_000:
            return 100
        elif depth > 100_000:
            return 80
        elif depth > 10_000:
            return 60
        else:
            return 40
    
    def _calculate_rating(self, volume: float, spread: float, depth: float) -> str:
        """计算综合评级"""
        score = (volume + spread + depth) / 3
        
        if score >= 90:
            return 'A'
        elif score >= 75:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'
    
    def _default_metrics(self) -> LiquidityMetrics:
        """默认指标"""
        return LiquidityMetrics(
            daily_volume=0,
            volume_score=0,
            spread=0,
            spread_score=0,
            depth=0,
            depth_score=0,
            slippage_estimate=0,
            liquidity_rating='D'
        )
    
    def compare_markets(self, symbols: List[str], market: str = 'binance') -> Dict:
        """
        比较多个资产的流动性
        """
        results = {}
        
        for symbol in symbols:
            try:
                metrics = self.analyze(symbol, market)
                results[symbol] = {
                    'rating': metrics.liquidity_rating,
                    'volume_score': metrics.volume_score,
                    'spread_score': metrics.spread_score,
                    'depth_score': metrics.depth_score,
                    'daily_volume': metrics.daily_volume
                }
            except Exception as e:
                print(f"分析 {symbol} 失败: {e}")
        
        return results


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("流动性分析器")
    print("=" * 50)
    
    # 创建分析器
    analyzer = LiquidityAnalyzer()
    
    # 分析BTC
    print("\n📊 BTCUSDT 流动性分析")
    metrics = analyzer.analyze("BTCUSDT", "binance")
    
    print(f"  日成交量: ${metrics.daily_volume:,.0f}")
    print(f"  成交量得分: {metrics.volume_score}")
    print(f"  买卖价差: {metrics.spread:.4%}")
    print(f"  价差得分: {metrics.spread_score}")
    print(f"  市场深度: ${metrics.depth:,.0f}")
    print(f"  深度得分: {metrics.depth_score}")
    print(f"  预估滑点: {metrics.slippage_estimate:.4%}")
    print(f"  流动性评级: {metrics.liquidity_rating}")
    
    # 比较多个币种
    print("\n📊 多币种流动性比较")
    results = analyzer.compare_markets([
        "BTCUSDT",
        "ETHUSDT", 
        "BNBUSDT",
        "SOLUSDT"
    ])
    
    for symbol, data in results.items():
        print(f"  {symbol}: {data['rating']} (成交量:{data['volume_score']}, 价差:{data['spread_score']}, 深度:{data['depth_score']})")
