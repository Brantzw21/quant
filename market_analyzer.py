"""
历史数据分析模块
- 趋势分析
- 波动率分析
- 支撑阻力位
- 周期性分析
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class MarketAnalyzer:
    """市场分析器"""
    
    def __init__(self, data_manager):
        self.dm = data_manager
    
    def analyze_trend(self, data, period=50):
        """分析趋势"""
        if len(data) < period:
            return None
        
        closes = [d['close'] for d in data]
        
        # 均线
        ma_short = np.mean(closes[-period//2:])
        ma_long = np.mean(closes[-period:])
        
        # 趋势判断
        if ma_short > ma_long * 1.02:
            trend = "上涨"
        elif ma_short < ma_long * 0.98:
            trend = "下跌"
        else:
            trend = "震荡"
        
        # 趋势强度
        volatility = np.std(closes[-period:]) / np.mean(closes[-period:])
        
        return {
            "trend": trend,
            "ma_short": round(ma_short, 2),
            "ma_long": round(ma_long, 2),
            "volatility": round(volatility * 100, 2),
            "price": closes[-1]
        }
    
    def analyze_volatility(self, data, period=30):
        """分析波动率"""
        if len(data) < period:
            return None
        
        closes = [d['close'] for d in data]
        returns = np.diff(closes) / closes[:-1]
        
        return {
            "daily_volatility": round(np.std(returns) * 100, 2),
            "annual_volatility": round(np.std(returns) * np.sqrt(365) * 100, 2),
            "max_drawdown": self._calc_max_drawdown(closes),
            "max_gain": round(max(returns) * 100, 2),
            "max_loss": round(min(returns) * 100, 2)
        }
    
    def _calc_max_drawdown(self, closes):
        """计算最大回撤"""
        peak = closes[0]
        max_dd = 0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak
            if dd > max_dd:
                max_dd = dd
        return round(max_dd * 100, 2)
    
    def find_support_resistance(self, data, period=50):
        """寻找支撑位和阻力位"""
        if len(data) < period:
            return None
        
        highs = [d['high'] for d in data[-period:]]
        lows = [d['low'] for d in data[-period:]]
        
        # 简化: 使用高低点
        resistance = max(highs)
        support = min(lows)
        current = data[-1]['close']
        
        return {
            "resistance": round(resistance, 2),
            "support": round(support, 2),
            "current": round(current, 2),
            "distance_to_resistance": round((resistance - current) / current * 100, 2),
            "distance_to_support": round((current - support) / support * 100, 2)
        }
    
    def analyze_volume(self, data, period=20):
        """分析成交量"""
        if len(data) < period:
            return None
        
        volumes = [d['volume'] for d in data[-period:]]
        avg_volume = np.mean(volumes)
        
        return {
            "avg_volume": round(avg_volume, 2),
            "current_volume": round(volumes[-1], 2),
            "volume_ratio": round(volumes[-1] / avg_volume, 2) if avg_volume > 0 else 0
        }
    
    def full_analysis(self, data):
        """完整分析"""
        return {
            "timestamp": datetime.now().isoformat(),
            "trend": self.analyze_trend(data),
            "volatility": self.analyze_volatility(data),
            "support_resistance": self.find_support_resistance(data),
            "volume": self.analyze_volume(data)
        }


def run_analysis(market='BTC', symbol='BTC/USDT', period='1h'):
    """运行分析"""
    from data_manager import get_data_manager
    
    dm = get_data_manager()
    
    if market == 'BTC':
        data = dm.get_btc_klines(period, limit=200)
    else:
        print(f"暂不支持 {market}")
        return
    
    if not data:
        print("无数据")
        return
    
    analyzer = MarketAnalyzer(dm)
    result = analyzer.full_analysis(data)
    
    print(f"\n📊 {symbol} 市场分析 ({period})")
    print(f"=" * 40)
    
    if result['trend']:
        t = result['trend']
        print(f"\n📈 趋势: {t['trend']}")
        print(f"   价格: {t['price']}")
        print(f"   波动率: {t['volatility']}%")
    
    if result['volatility']:
        v = result['volatility']
        print(f"\n📉 波动率:")
        print(f"   年化: {v['annual_volatility']}%")
        print(f"   最大回撤: {v['max_drawdown']}%")
    
    if result['support_resistance']:
        sr = result['support_resistance']
        print(f"\n🎯 支撑/阻力:")
        print(f"   阻力: {sr['distance_to_resistance']:+.1f}% ({sr['resistance']})")
        print(f"   支撑: {sr['distance_to_support']:+.1f}% ({sr['support']})")
    
    return result


if __name__ == '__main__':
    import sys
    market = sys.argv[1] if len(sys.argv) > 1 else 'BTC'
    period = sys.argv[2] if len(sys.argv) > 2 else '1h'
    run_analysis(market, period=period)
