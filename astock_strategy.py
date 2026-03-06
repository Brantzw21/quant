#!/usr/bin/env python3
"""
A股模拟交易策略
基于沪深300指数
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import MarketDataManager
import pandas as pd
from notify import send_message
from datetime import datetime

class AStockStrategy:
    """A股策略"""
    
    def __init__(self, symbol="sh.000300", name="沪深300"):
        self.symbol = symbol
        self.name = name
        self.dm = MarketDataManager()
        
    def calculate_indicators(self, df):
        """计算技术指标"""
        # 转换为DataFrame
        data = pd.DataFrame(df)
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)
        
        # MA
        data['ma5'] = data['close'].rolling(5).mean()
        data['ma20'] = data['close'].rolling(20).mean()
        data['ma60'] = data['close'].rolling(60).mean()
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # 成交量确认
        data['vol_ma'] = data['volume'].rolling(20).mean()
        
        return data
    
    def analyze(self, data):
        """分析信号"""
        if len(data) < 60:
            return {"signal": "HOLD", "confidence": 0, "reason": "数据不足"}
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 趋势判断
        trend_up = latest['ma20'] > latest['ma60']
        trend_down = latest['ma20'] < latest['ma60']
        
        # RSI
        rsi = latest['rsi']
        oversold = rsi < 30
        overbought = rsi > 70
        
        # 成交量
        vol_confirm = latest['volume'] > latest['vol_ma'] * 0.8
        
        # 信号判断
        signals = []
        
        # 买入条件
        if trend_up and (oversold or rsi < 40) and vol_confirm:
            signals.append("BUY")
        elif trend_up and latest['close'] > latest['ma5'] and latest['ma5'] > latest['ma20']:
            signals.append("BUY")
            
        # 卖出条件
        if trend_down and (overbought or rsi > 60):
            signals.append("SELL")
        elif trend_down and latest['close'] < latest['ma5']:
            signals.append("SELL")
        
        # 止损检查
        if latest['close'] < latest['ma20'] * 0.95:  # 跌破MA20 5%
            signals.append("SELL")
        
        # 统计信号
        buy_count = signals.count("BUY")
        sell_count = signals.count("SELL")
        
        if buy_count > sell_count:
            signal = "BUY"
            confidence = min(0.6 + buy_count * 0.1, 0.9)
        elif sell_count > buy_count:
            signal = "SELL"
            confidence = min(0.6 + sell_count * 0.1, 0.9)
        else:
            signal = "HOLD"
            confidence = 0.5
        
        return {
            "signal": signal,
            "confidence": confidence,
            "price": latest['close'],
            "ma20": latest['ma20'],
            "ma60": latest['ma60'],
            "rsi": rsi,
            "trend": "up" if trend_up else "down" if trend_down else "sideways",
            "volume": latest['volume'],
            "reason": "; ".join(signals) if signals else "无明确信号"
        }
    
    def run(self):
        """运行策略"""
        print(f"=== A股策略: {self.name} ===")
        
        # 获取数据
        df = self.dm.get_a_stock_klines(self.symbol, '2024-01-01', datetime.now().strftime('%Y-%m-%d'))
        
        if not df or len(df) < 60:
            print("数据不足")
            return None
        
        # 计算指标
        data = self.calculate_indicators(df)
        
        # 分析信号
        result = self.analyze(data)
        
        # 输出结果
        print(f"代码: {self.symbol}")
        print(f"名称: {self.name}")
        print(f"价格: {result['price']:.2f}")
        print(f"趋势: {result['trend']}")
        print(f"MA20: {result['ma20']:.2f}")
        print(f"MA60: {result['ma60']:.2f}")
        print(f"RSI: {result['rsi']:.2f}")
        print(f"信号: {result['signal']} (置信度: {result['confidence']:.0%})")
        print(f"原因: {result['reason']}")
        
        return result


def main():
    strategy = AStockStrategy()
    result = strategy.run()
    
    if result:
        # 发送通知
        msg = f"""
📊 A股策略信号 - {strategy.name}

价格: {result['price']:.2f}
趋势: {result['trend']}
RSI: {result['rsi']:.2f}

📌 信号: {result['signal']} (置信度 {result['confidence']:.0%})
原因: {result['reason']}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        send_message(msg)


if __name__ == "__main__":
    main()
