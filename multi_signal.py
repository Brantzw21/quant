#!/usr/bin/env python3
"""
多市场信号生成器
统一接口生成各市场的交易信号
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from typing import Dict, Optional
from datetime import datetime
import json


class SignalGenerator:
    """
    多市场信号生成器
    
    支持:
    - 数字货币 (Binance)
    - A股 (Baostock)
    - 美股 (IBKR/YFinance)
    """
    
    def __init__(self):
        self.last_signal = {}
    
    def generate_crypto_signal(self, symbol: str = "BTCUSDT") -> Dict:
        """
        生成数字货币信号
        
        Returns:
            {
                'market': 'crypto',
                'symbol': 'BTCUSDT',
                'signal': 'BUY'|'SELL'|'HOLD',
                'confidence': 0.0-1.0,
                'price': 50000.0,
                'rsi': 45.0,
                'trend': 'bullish'|'bearish'|'neutral',
                'timestamp': '2026-01-01T00:00:00'
            }
        """
        try:
            # 导入Binance
            from config import API_KEY, SECRET_KEY, TESTNET
            from binance.client import Client
            from light_strategy import generate_signal
            
            client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
            
            # 获取K线
            klines = client.get_klines(symbol=symbol, interval="4h", limit=100)
            
            # 转换为DataFrame
            import pandas as pd
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_base', 'taker_quote', 'ignore'
            ])
            
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # 获取信号
            signal = generate_signal(symbol)
            
            current_price = df['close'].iloc[-1]
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 判断趋势
            ma20 = df['close'].rolling(20).mean()
            ma50 = df['close'].rolling(50).mean()
            
            if current_price > ma20.iloc[-1] > ma50.iloc[-1]:
                trend = "bullish"
            elif current_price < ma20.iloc[-1] < ma50.iloc[-1]:
                trend = "bearish"
            else:
                trend = "neutral"
            
            result = {
                'market': 'crypto',
                'symbol': symbol,
                'signal': signal.get('signal', 'HOLD'),
                'confidence': signal.get('confidence', 0.5),
                'price': current_price,
                'rsi': round(current_rsi, 2) if not pd.isna(current_rsi) else 50,
                'trend': trend,
                'timestamp': datetime.now().isoformat()
            }
            
            self.last_signal = result
            return result
            
        except Exception as e:
            print(f"生成数字货币信号失败: {e}")
            return {'error': str(e)}
    
    def generate_astock_signal(self, symbol: str = "sh.000001") -> Dict:
        """
        生成A股信号
        
        Returns:
            {
                'market': 'astock',
                'symbol': 'sh.000001',
                'signal': 'BUY'|'SELL'|'HOLD',
                'confidence': 0.0-1.0,
                'price': 3000.0,
                'timestamp': '2026-01-01T00:00:00'
            }
        """
        try:
            from astock_data import AStockDataManager
            
            dm = AStockDataManager(source="baostock")
            
            # 获取数据
            df = dm.get_kline(symbol, start_date="2024-01-01")
            
            if df.empty:
                return {'error': '无数据'}
            
            # 最新价格
            current_price = float(df['close'].iloc[-1])
            
            # 简单均线策略
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            
            ma20 = df['ma20'].iloc[-1]
            ma60 = df['ma60'].iloc[-1]
            
            # 判断信号
            if ma20 > ma60 * 1.02:  # 均线多头
                signal = "BUY"
                confidence = 0.65
            elif ma20 < ma60 * 0.98:  # 均线空头
                signal = "SELL"
                confidence = 0.65
            else:
                signal = "HOLD"
                confidence = 0.5
            
            dm.disconnect()
            
            result = {
                'market': 'astock',
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
            self.last_signal = result
            return result
            
        except Exception as e:
            print(f"生成A股信号失败: {e}")
            return {'error': str(e)}
    
    def generate_usstock_signal(self, symbol: str = "SPY") -> Dict:
        """
        生成美股信号
        
        Returns:
            {
                'market': 'us_stock',
                'symbol': 'SPY',
                'signal': 'BUY'|'SELL'|'HOLD',
                'confidence': 0.0-1.0,
                'price': 450.0,
                'timestamp': '2026-01-01T00:00:00'
            }
        """
        try:
            import yfinance as yf
            
            # 获取数据
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y")
            
            if df.empty:
                return {'error': '无数据'}
            
            # 最新价格
            current_price = float(df['Close'].iloc[-1])
            
            # 简单均线策略
            df['ma20'] = df['Close'].rolling(20).mean()
            df['ma50'] = df['Close'].rolling(50).mean()
            
            ma20 = df['ma20'].iloc[-1]
            ma50 = df['ma50'].iloc[-1]
            
            # 判断信号
            if ma20 > ma50 * 1.02:
                signal = "BUY"
                confidence = 0.65
            elif ma20 < ma50 * 0.98:
                signal = "SELL"
                confidence = 0.65
            else:
                signal = "HOLD"
                confidence = 0.5
            
            result = {
                'market': 'us_stock',
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
            self.last_signal = result
            return result
            
        except Exception as e:
            print(f"生成美股信号失败: {e}")
            return {'error': str(e)}
    
    def generate_all_signals(self) -> Dict:
        """生成所有市场信号"""
        signals = {
            'timestamp': datetime.now().isoformat(),
            'markets': {}
        }
        
        # 数字货币
        signals['markets']['crypto'] = {
            'BTCUSDT': self.generate_crypto_signal('BTCUSDT'),
            'ETHUSDT': self.generate_crypto_signal('ETHUSDT'),
        }
        
        # A股
        signals['markets']['astock'] = {
            'sh.000001': self.generate_astock_signal('sh.000001'),
            'sh.000300': self.generate_astock_signal('sh.000300'),
        }
        
        # 美股
        signals['markets']['us_stock'] = {
            'SPY': self.generate_usstock_signal('SPY'),
            'QQQ': self.generate_usstock_signal('QQQ'),
        }
        
        return signals
    
    def save_signals(self, filepath: str = "/root/.openclaw/workspace/quant/quant/data/all_signals.json"):
        """保存信号到文件"""
        signals = self.generate_all_signals()
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(signals, f, indent=2, ensure_ascii=False)
        
        return signals


# ==================== 使用示例 ====================

if __name__ == "__main__":
    generator = SignalGenerator()
    
    print("=" * 50)
    print("多市场信号生成")
    print("=" * 50)
    
    # 生成各市场信号
    print("\n📊 BTC信号:")
    print(generator.generate_crypto_signal('BTCUSDT'))
    
    print("\n📊 A股信号:")
    print(generator.generate_astock_signal('sh.000300'))
    
    print("\n📊 美股信号:")
    print(generator.generate_usstock_signal('SPY'))
    
    # 保存所有信号
    print("\n保存信号到文件...")
    signals = generator.save_signals()
    print("✅ 已保存")
