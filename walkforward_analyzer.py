#!/usr/bin/env python3
"""
Walk-Forward 回测分析
验证策略在样本外数据的表现
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from light_strategy import generate_signal, calculate_indicators, analyze_trend
from data_manager import DataManager
import json

class WalkForwardAnalyzer:
    """
    Walk-Forward 分析器
    
    将数据分为:
    - In-Sample (IS): 参数优化期
    - Out-of-Sample (OOS): 验证期
    
    滚动窗口执行
    """
    
    def __init__(self, symbol="BTCUSDT", intervals=["4h"]):
        self.symbol = symbol
        self.intervals = intervals
        self.dm = DataManager()
        
        # Walk-Forward 参数
        self.is_period_days = 90   # 样本内天数 (参数优化)
        self.oos_period_days = 30   # 样本外天数 (验证)
        self.step_days = 15         # 滚动步长
        
    def get_data(self, start_date, end_date):
        """获取历史数据"""
        df = self.dm.get_binance_klines(
            symbol=self.symbol,
            interval="4h",
            start=start_date,
            end=end_date
        )
        return df
    
    def run_strategy_on_data(self, df):
        """在数据上运行策略"""
        if len(df) < 50:
            return []
        
        df = calculate_indicators(df.copy())
        
        signals = []
        for i in range(50, len(df)):
            row = df.iloc[i]
            analysis = analyze_trend(df.iloc[:i+1])
            
            signals.append({
                "date": str(df.index[i]) if hasattr(df.index, '__getitem__') else str(row.name),
                "price": row['close'],
                "signal": "BUY" if analysis.get('trend_up') and analysis.get('trend_strong') else "SELL" if analysis.get('trend_down') and analysis.get('trend_strong') else "HOLD",
                "trend": analysis.get('trend'),
                "rsi": analysis.get('rsi'),
                "adx": analysis.get('adx')
            })
        
        return signals
    
    def calculate_returns(self, signals, initial_capital=10000):
        """计算策略收益"""
        capital = initial_capital
        position = 0
        trades = []
        
        for i, sig in enumerate(signals):
            if sig['signal'] == 'BUY' and position == 0:
                position = capital / sig['price']
                capital = 0
                trades.append({"type": "BUY", "price": sig['price'], "date": sig['date']})
            elif sig['signal'] == 'SELL' and position > 0:
                capital = position * sig['price']
                trades.append({"type": "SELL", "price": sig['price'], "date": sig['date'], "pnl": capital - trades[-1]['price'] * position})
                position = 0
        
        # 最终持仓
        if position > 0:
            capital = position * signals[-1]['price']
        
        total_return = (capital - initial_capital) / initial_capital * 100
        return {
            "total_return": total_return,
            "final_capital": capital,
            "num_trades": len(trades),
            "trades": trades
        }
    
    def run(self, start_date, end_date):
        """运行Walk-Forward分析"""
        print(f"📊 Walk-Forward 分析: {start_date} ~ {end_date}")
        
        # 获取全量数据
        df = self.get_data(start_date, end_date)
        
        if len(df) < self.is_period_days + self.oos_period_days:
            print("数据不足")
            return None
        
        results = []
        current_start = start_date
        
        while True:
            # 样本内期间
            is_end = current_start + timedelta(days=self.is_period_days)
            # 样本外期间
            oos_end = is_end + timedelta(days=self.oos_period_days)
            
            if oos_end > end_date:
                break
            
            # 获取样本内数据（用于参数优化模拟）
            is_data = df[(df.index >= current_start) & (df.index < is_end)]
            # 获取样本外数据（用于验证）
            oos_data = df[(df.index >= is_end) & (df.index < oos_end)]
            
            if len(is_data) < 50 or len(oos_data) < 20:
                current_start += timedelta(days=self.step_days)
                continue
            
            # 在样本外数据上运行策略
            oos_signals = self.run_strategy_on_data(oos_data)
            oos_returns = self.calculate_returns(oos_signals)
            
            results.append({
                "period": f"{is_end.strftime('%Y-%m-%d')}~{oos_end.strftime('%Y-%m-%d')}",
                "is_start": str(current_start.date()),
                "is_end": str(is_end.date()),
                "oos_start": str(is_end.date()),
                "oos_end": str(oos_end.date()),
                "oos_return": oos_returns['total_return'],
                "oos_trades": oos_returns['num_trades'],
                "final_capital": oos_returns['final_capital']
            })
            
            print(f"  {is_end.strftime('%Y-%m-%d')}~{oos_end.strftime('%Y-%m-%d')}: "
                  f"OOS收益={oos_returns['total_return']:.2f}%, 交易数={oos_returns['num_trades']}")
            
            current_start += timedelta(days=self.step_days)
        
        # 汇总
        if results:
            avg_return = np.mean([r['oos_return'] for r in results])
            win_rate = len([r for r in results if r['oos_return'] > 0]) / len(results) * 100
            
            summary = {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "num_periods": len(results),
                "avg_oos_return": round(avg_return, 2),
                "win_rate": round(win_rate, 2),
                "results": results
            }
            
            print(f"\n📈 汇总:")
            print(f"  平均样本外收益: {avg_return:.2f}%")
            print(f"  胜率: {win_rate:.1f}%")
            
            return summary
        
        return None

def main():
    """主函数"""
    # 最近2年数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    analyzer = WalkForwardAnalyzer(symbol="BTCUSDT")
    results = analyzer.run(start_date, end_date)
    
    if results:
        # 保存结果
        output_file = "/root/.openclaw/workspace/quant_v2/logs/walkforward_results.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 结果已保存到 {output_file}")

if __name__ == "__main__":
    main()
