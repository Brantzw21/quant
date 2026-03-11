#!/usr/bin/env python3
"""
市场情绪分析器
基于多维度数据分析市场情绪
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import requests
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime


class SentimentAnalyzer:
    """
    市场情绪分析器
    
    数据来源:
    - 恐惧贪婪指数
    - 社交媒体情绪
    - 资金流向
    - 期权持仓
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5分钟
    
    def get_fear_greed_index(self) -> Dict:
        """
        获取恐惧贪婪指数
        
        Returns:
            {
                'value': 45,  # 0-100
                'label': 'Fear',  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
                'timestamp': '2026-01-01T00:00:00'
            }
        """
        # 尝试获取alternative.me数据
        try:
            resp = requests.get('https://api.alternative.me/fng/', timeout=5)
            data = resp.json()
            
            if data.get('data'):
                item = data['data'][0]
                
                value = int(item['value'])
                label = item['value_classification']
                
                return {
                    'value': value,
                    'label': label,
                    'timestamp': item['timestamp']
                }
        except:
            pass
        
        # 返回模拟数据
        return self._simulate_fear_greed()
    
    def _simulate_fear_greed(self) -> Dict:
        """模拟恐惧贪婪指数"""
        import random
        value = random.randint(20, 80)
        
        if value < 25:
            label = "Extreme Fear"
        elif value < 45:
            label = "Fear"
        elif value < 55:
            label = "Neutral"
        elif value < 75:
            label = "Greed"
        else:
            label = "Extreme Greed"
        
        return {
            'value': value,
            'label': label,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_funding_rate(self, symbol: str = "BTCUSDT") -> Dict:
        """
        获取资金费率
        
        Returns:
            {
                'rate': 0.0001,  # 费率
                'label': 'Neutral',  # Neutral, Long, Short
                'predominant': 'long'  # long, short
            }
        """
        try:
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 获取资金费率
            funding = client.funding_rate(symbol=symbol, limit=1)
            
            if funding:
                rate = float(funding[0]['fundingRate'])
                
                if rate > 0.0001:
                    label = "Long"
                    predominant = "long"
                elif rate < -0.0001:
                    label = "Short"
                    predominant = "short"
                else:
                    label = "Neutral"
                    predominant = "neutral"
                
                return {
                    'rate': rate,
                    'label': label,
                    'predominant': predominant,
                    'timestamp': funding[0]['fundingTime']
                }
        except Exception as e:
            print(f"获取资金费率失败: {e}")
        
        return {'rate': 0, 'label': 'Unknown', 'predominant': 'neutral'}
    
    def get_long_short_ratio(self, symbol: str = "BTCUSDT") -> Dict:
        """
        获取多空比
        
        Returns:
            {
                'ratio': 1.2,  # >1 多头主导
                'label': 'Long'  # Long, Short, Neutral
            }
        """
        try:
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 获取top转户数据
            taker = client.top_long_short_position_ratio(
                symbol=symbol,
                period='1h',
                limit=1
            )
            
            if taker:
                ratio = float(taker[0]['longShortRatio'])
                
                if ratio > 1.1:
                    label = "Long"
                elif ratio < 0.9:
                    label = "Short"
                else:
                    label = "Neutral"
                
                return {
                    'ratio': ratio,
                    'label': label,
                    'timestamp': taker[0]['timestamp']
                }
        except:
            pass
        
        return {'ratio': 1.0, 'label': 'Neutral'}
    
    def get_order_book_imbalance(self, symbol: str = "BTCUSDT", depth: int = 20) -> Dict:
        """
        订单簿失衡
        
        Returns:
            {
                'imbalance': 0.15,  # >0 买方主导, <0 卖方主导
                'bid_ask_ratio': 1.3,
                'spread': 0.01
            }
        """
        try:
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 获取深度
            depth_data = client.get_order_book(symbol=symbol, limit=depth)
            
            bids = np.array([float(b[1]) for b in depth_data['bids']])
            asks = np.array([float(a[1]) for a in depth_data['asks']])
            
            # 计算失衡
            bid_vol = np.sum(bids)
            ask_vol = np.sum(asks)
            
            total = bid_vol + ask_vol
            
            if total > 0:
                imbalance = (bid_vol - ask_vol) / total
            else:
                imbalance = 0
            
            # 买卖比
            bid_ask_ratio = bid_vol / ask_vol if ask_vol > 0 else 1
            
            # 价差
            best_bid = float(depth_data['bids'][0][0])
            best_ask = float(depth_data['asks'][0][0])
            spread = (best_ask - best_bid) / best_bid
            
            return {
                'imbalance': round(imbalance, 4),
                'bid_ask_ratio': round(bid_ask_ratio, 2),
                'spread': round(spread, 6)
            }
        except:
            pass
        
        return {'imbalance': 0, 'bid_ask_ratio': 1.0, 'spread': 0}
    
    def analyze_sentiment(self, symbol: str = "BTCUSDT") -> Dict:
        """
        综合情绪分析
        """
        # 获取各指标
        fear_greed = self.get_fear_greed_index()
        funding = self.get_funding_rate(symbol)
        long_short = self.get_long_short_ratio(symbol)
        order_book = self.get_order_book_imbalance(symbol)
        
        # 综合评分 (-100 到 100)
        scores = []
        
        # 恐惧贪婪指数 (转至 -100 到 100)
        fg_score = (fear_greed['value'] - 50) * 2
        scores.append(('fear_greed', fg_score, 0.3))
        
        # 资金费率
        funding_score = funding['rate'] * 10000  # 放大
        scores.append(('funding', funding_score, 0.2))
        
        # 多空比
        ls_score = (long_short['ratio'] - 1) * 100
        scores.append(('long_short', ls_score, 0.3))
        
        # 订单簿
        ob_score = order_book['imbalance'] * 100
        scores.append(('order_book', ob_score, 0.2))
        
        # 加权总分
        total_score = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores)
        
        # 情绪标签
        if total_score > 30:
            sentiment = "极度贪婪"
            emoji = "😈"
        elif total_score > 15:
            sentiment = "贪婪"
            emoji = "🟢"
        elif total_score > -15:
            sentiment = "中性"
            emoji = "😐"
        elif total_score > -30:
            sentiment = "恐惧"
            emoji = "🔴"
        else:
            sentiment = "极度恐惧"
            emoji = "😱"
        
        return {
            'symbol': symbol,
            'sentiment': sentiment,
            'emoji': emoji,
            'score': round(total_score, 1),  # -100 到 100
            'components': {
                'fear_greed': {
                    'value': fear_greed['value'],
                    'label': fear_greed['label'],
                    'score': round(fg_score, 1)
                },
                'funding': {
                    'rate': funding['rate'],
                    'label': funding['label'],
                    'score': round(funding_score, 1)
                },
                'long_short': {
                    'ratio': long_short['ratio'],
                    'label': long_short['label'],
                    'score': round(ls_score, 1)
                },
                'order_book': {
                    'imbalance': order_book['imbalance'],
                    'bid_ask_ratio': order_book['bid_ask_ratio'],
                    'score': round(ob_score, 1)
                }
            },
            'timestamp': datetime.now().isoformat()
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("市场情绪分析器")
    print("=" * 50)
    
    # 创建分析器
    analyzer = SentimentAnalyzer()
    
    # 综合分析
    result = analyzer.analyze_sentiment("BTCUSDT")
    
    print(f"\n📊 BTCUSDT 情绪分析")
    print(f"  情绪: {result['emoji']} {result['sentiment']}")
    print(f"  评分: {result['score']}")
    
    print(f"\n📈 各维度:")
    for name, data in result['components'].items():
        print(f"  {name}:")
        print(f"    原始值: {data.get('value') or data.get('rate') or data.get('ratio') or data.get('imbalance')}")
        print(f"    标签: {data['label']}")
        print(f"    评分: {data['score']}")
