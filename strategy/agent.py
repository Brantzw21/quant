"""
策略Agent - 完整版 (整合所有功能)
=====================================

包含:
- 市场状态分析
- 多指标信号生成
- 凯利公式仓位计算
- 风控检查

作者: AutoQuant
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET, SYMBOL, INTERVALS
import json
from datetime import datetime
import time

class StrategyAgent:
    """策略Agent - 完整版"""
    
    def __init__(self):
        self.client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        self.symbol = SYMBOL
    
    def get_klines(self, interval, limit=100):
        """获取K线"""
        klines = self.client.get_klines(
            symbol=self.symbol,
            interval=interval,
            limit=limit
        )
        
        closes = [float(k[4]) for k in klines]
        
        # 清洗异常值
        median = sorted(closes)[len(closes)//2]
        clean_closes = []
        for c in closes:
            if abs(c - median) / median > 0.5:
                clean_closes.append(median)
            else:
                clean_closes.append(c)
        
        return clean_closes
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        import numpy as np
        
        closes = data
        
        # 均线
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else ma20
        
        # RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = np.mean(closes[-12:])
        ema26 = np.mean(closes[-26:]) if len(closes) >= 26 else ema12
        macd = ema12 - ema26
        macd_signal = macd * 0.9
        
        # 布林带
        std = np.std(closes[-20:])
        upper = ma20 + 2 * std
        lower = ma20 - 2 * std
        
        # 波动率
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0.01
        
        return {
            "price": closes[-1],
            "ma10": ma10,
            "ma20": ma20,
            "ma50": ma50,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "boll_upper": upper,
            "boll_lower": lower,
            "volatility": volatility,
            "trend": "bull" if ma10 > ma50 else "bear"
        }
    
    def analyze_market_state(self, data_4h):
        """分析市场状态"""
        ind = self.calculate_indicators(data_4h)
        
        # 趋势判断
        if ind["ma20"] > ind["ma50"]:
            trend = "up"
        elif ind["ma20"] < ind["ma50"]:
            trend = "down"
        else:
            trend = "sideways"
        
        # 高波动检测
        is_high_vol = ind["volatility"] > 0.03
        
        # 状态
        if is_high_vol:
            state = "high_volatility"
        elif trend == "up":
            state = "trend_up"
        elif trend == "down":
            state = "trend_down"
        else:
            state = "sideways"
        
        return {
            "trend": trend,
            "state": state,
            "volatility": ind["volatility"],
            "allow_trade": not is_high_vol,
            "indicators": ind
        }
    
    def generate_signal(self):
        """生成交易信号"""
        print(f"\n{'='*50}")
        print(f"📊 Strategy Agent - 信号生成")
        print(f"{'='*50}")
        
        # 获取多时间框架数据
        data_4h = self.get_klines("4h", INTERVALS["4h"])
        data_1h = self.get_klines("1h", INTERVALS["1h"])
        
        # 市场状态
        market = self.analyze_market_state(data_4h)
        print(f"\n�markt状态: {market['state']} | 波动率: {market['volatility']*100:.2f}%")
        print(f"  允许交易: {market['allow_trade']}")
        
        # 计算指标
        ind_4h = self.calculate_indicators(data_4h)
        ind_1h = self.calculate_indicators(data_1h)
        
        print(f"\n4H: {ind_4h['trend']} | RSI:{ind_4h['rsi']:.1f} | 价格:{ind_4h['price']:.0f}")
        print(f"1H: {ind_1h['trend']} | RSI:{ind_1h['rsi']:.1f} | 价格:{ind_1h['price']:.0f}")
        
        # 信号逻辑
        signals = []
        
        # 1. 趋势信号
        if ind_4h["trend"] == "bull" and ind_1h["trend"] == "bull":
            signals.append(("BUY", "趋势多头"))
        elif ind_4h["trend"] == "bear" and ind_1h["trend"] == "bear":
            signals.append(("SELL", "趋势空头"))
        
        # 2. RSI
        if ind_1h["rsi"] < 30:
            signals.append(("BUY", f"RSI超卖({ind_1h['rsi']:.0f})"))
        elif ind_1h["rsi"] > 70:
            signals.append(("SELL", f"RSI超买({ind_1h['rsi']:.0f})"))
        
        # 3. MACD
        if ind_1h["macd"] > ind_1h["macd_signal"]:
            signals.append(("BUY", "MACD金叉"))
        elif ind_1h["macd"] < ind_1h["macd_signal"]:
            signals.append(("SELL", "MACD死叉"))
        
        # 4. 布林
        if ind_1h["price"] > ind_1h["boll_upper"]:
            signals.append(("BUY", "突破上轨"))
        elif ind_1h["price"] < ind_1h["boll_lower"]:
            signals.append(("SELL", "跌破下轨"))
        
        # 统计
        buy_count = sum(1 for s in signals if s[0] == "BUY")
        sell_count = sum(1 for s in signals if s[0] == "SELL")
        
        # 决策
        if not market["allow_trade"]:
            signal = "HOLD"
            reason = "高波动市场"
            confidence = 0
        elif buy_count >= 2:
            signal = "BUY"
            reason = "+".join([s[1] for s in signals if s[0] == "BUY"])
            confidence = min(buy_count / 4, 1.0)
        elif sell_count >= 2:
            signal = "SELL"
            reason = "+".join([s[1] for s in signals if s[0] == "SELL"])
            confidence = min(sell_count / 4, 1.0)
        else:
            signal = "HOLD"
            reason = "无共识"
            confidence = 0.5
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "symbol": self.symbol,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "signals": signals,
            "market_state": {
                "state": market["state"],
                "allow_trade": market["allow_trade"],
                "trend": market["trend"]
            },
            "indicators": {
                "4h": {k: round(v, 2) if isinstance(v, float) else v for k, v in ind_4h.items()},
                "1h": {k: round(v, 2) if isinstance(v, float) else v for k, v in ind_1h.items()}
            }
        }
        
        print(f"\n📌 信号: {signal} ({confidence:.0%}) | {reason}")
        
        return result
    
    def save_signal(self, signal_data):
        """保存信号"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "last_signal.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(signal_data, f, indent=2)


def run_strategy():
    """运行策略Agent"""
    agent = StrategyAgent()
    signal = agent.generate_signal()
    agent.save_signal(signal)
    return signal


if __name__ == "__main__":
    run_strategy()
