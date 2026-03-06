#!/usr/bin/env python3
"""
A股多标的策略
支持: 沪深300, 上证50, 创业板, 中证500, 券商ETF等
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import MarketDataManager
from astock_config import ALL_TARGETS, A_STOCK_ETFS, A_STOCK_INDEXES, PREFERRED_SOURCE
import pandas as pd
from notify import send_message
from datetime import datetime
import json

class AStockMultiStrategy:
    """A股多标的策略"""
    
    def __init__(self):
        self.dm = MarketDataManager()
        self.targets = ALL_TARGETS
        
    def calculate_indicators(self, df):
        """计算技术指标"""
        data = pd.DataFrame(df)
        if 'datetime' not in data.columns:
            return None
            
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)
        
        # MA
        data['ma5'] = data['close'].rolling(5).mean()
        data['ma10'] = data['close'].rolling(10).mean()
        data['ma20'] = data['close'].rolling(20).mean()
        data['ma60'] = data['close'].rolling(60).mean()
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['macd'] = exp1 - exp2
        data['signal'] = data['macd'].ewm(span=9, adjust=False).mean()
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # 成交量
        data['vol_ma5'] = data['volume'].rolling(5).mean()
        data['vol_ma20'] = data['volume'].rolling(20).mean()
        
        return data
    
    def analyze_single(self, code, name, data):
        """分析单个标的"""
        if data is None or len(data) < 60:
            return None
        
        latest = data.iloc[-1]
        
        # 趋势判断
        trend_up = latest['ma20'] > latest['ma60']
        trend_down = latest['ma20'] < latest['ma60']
        
        # RSI
        rsi = latest['rsi']
        
        # MACD金叉死叉
        macd_cross = ""
        if latest['macd'] > latest['signal'] and data.iloc[-2]['macd'] <= data.iloc[-2]['signal']:
            macd_cross = "GOLDEN"
        elif latest['macd'] < latest['signal'] and data.iloc[-2]['macd'] >= data.iloc[-2]['signal']:
            macd_cross = "DEAD"
        
        # 成交量
        vol_confirm = latest['volume'] > latest['vol_ma20'] * 0.8
        
        # 信号判断
        score = 0
        reasons = []
        
        # 上涨趋势
        if trend_up:
            score += 1
            reasons.append("MA20>MA60")
        
        # RSI低位金叉
        if rsi < 30:
            score += 1
            reasons.append("RSI超卖")
        elif rsi > 70:
            score -= 1
            reasons.append("RSI超买")
            
        # MACD金叉
        if macd_cross == "GOLDEN":
            score += 1
            reasons.append("MACD金叉")
        elif macd_cross == "DEAD":
            score -= 1
            reasons.append("MACD死叉")
        
        # 成交量确认
        if vol_confirm:
            score += 0.5
            reasons.append("成交量放大")
        
        # 突破新高
        if latest['close'] > data.iloc[-20:]['high'].max() * 0.98:
            score += 1
            reasons.append("突破20日高点")
        
        # 最终信号
        if score >= 2:
            signal = "BUY"
            confidence = min(0.5 + score * 0.15, 0.9)
        elif score <= -1:
            signal = "SELL"
            confidence = min(0.5 + abs(score) * 0.15, 0.9)
        else:
            signal = "HOLD"
            confidence = 0.5
        
        return {
            "code": code,
            "name": name,
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "price": latest['close'],
            "change": ((latest['close'] - data.iloc[-2]['close']) / data.iloc[-2]['close'] * 100) if len(data) > 1 else 0,
            "rsi": round(rsi, 2),
            "trend": "up" if trend_up else "down" if trend_down else "sideways",
            "macd_cross": macd_cross,
            "reasons": "; ".join(reasons) if reasons else "观望"
        }
    
    def run(self, targets=None):
        """运行多标的策略"""
        if targets is None:
            targets = self.targets
            
        print(f"=== A股多标的策略 ({len(targets)}个标的) ===")
        
        results = []
        
        for target in targets:
            try:
                code = target['code']
                name = target['name']
                
                # 获取数据
                df = self.dm.get_a_stock_klines(code, '2024-01-01', datetime.now().strftime('%Y-%m-%d'))
                
                if not df or len(df) < 60:
                    continue
                
                # 计算指标
                data = self.calculate_indicators(df)
                
                # 分析
                result = self.analyze_single(code, name, data)
                if result:
                    results.append(result)
                    
            except Exception as e:
                print(f"  {target['name']}: 错误 - {e}")
                continue
        
        # 按置信度排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 输出结果
        print(f"\n{'代码':<12} {'名称':<12} {'价格':<10} {'涨跌':<8} {'RSI':<6} {'趋势':<6} {'信号':<6} {'置信度':<8}")
        print("-" * 80)
        
        for r in results:
            emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⏸️"}.get(r['signal'], "❓")
            print(f"{r['code']:<12} {r['name']:<12} {r['price']:<10.2f} {r['change']:+7.2f}% {r['rsi']:<6} {r['trend']:<6} {emoji} {r['signal']:<6} {r['confidence']:.0%}")
        
        # 推荐标的
        buy_signals = [r for r in results if r['signal'] == 'BUY']
        sell_signals = [r for r in results if r['signal'] == 'SELL']
        
        print(f"\n📊 汇总: 买入信号 {len(buy_signals)}个, 卖出信号 {len(sell_signals)}个, 观望 {len(results)-len(buy_signals)-len(sell_signals)}个")
        
        return results
    
    def get_recommendation(self, targets=None):
        """获取推荐标的"""
        results = self.run(targets)
        
        if not results:
            return None
            
        # 推荐买入
        buy = [r for r in results if r['signal'] == 'BUY']
        
        return {
            "buy": buy[:3] if buy else [],  # 推荐最多3个
            "sell": [r for r in results if r['signal'] == 'SELL'][:3],
            "all": results
        }


def main():
    strategy = AStockMultiStrategy()
    
    # 运行ETF策略
    print("\n" + "="*50)
    print("【ETF策略】")
    print("="*50)
    etf_results = strategy.get_recommendation(A_STOCK_ETFS)
    
    # 运行指数策略
    print("\n" + "="*50)
    print("【指数策略】")
    print("="*50)
    index_results = strategy.get_recommendation(A_STOCK_INDEXES)
    
    # 生成通知消息
    msg = f"""
📈 A股多标的策略信号 - {datetime.now().strftime('%Y-%m-%d %H:%M')}

【ETF推荐】
"""
    
    if etf_results['buy']:
        for r in etf_results['buy'][:3]:
            msg += f"🟢 {r['name']} ({r['code']}) {r['signal']} {r['confidence']:.0%}\n"
    else:
        msg += "无买入信号\n"
    
    msg += "\n【指数推荐】\n"
    if index_results['buy']:
        for r in index_results['buy'][:3]:
            msg += f"🟢 {r['name']} ({r['code']}) {r['signal']} {r['confidence']:.0%}\n"
    else:
        msg += "无买入信号\n"
    
    msg += f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # 发送通知
    send_message(msg)
    
    # 保存结果
    with open('/root/.openclaw/workspace/quant/quant/data/astock_signals.json', 'w') as f:
        json.dump({
            "etf": etf_results,
            "index": index_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
