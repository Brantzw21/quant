#!/usr/bin/env python3
"""
Walk-Forward 回测分析
验证策略在样本外数据的表现

基于统一回测框架 backtest_framework.py
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

from backtest_framework import Backtester, BacktestConfig
from data_pipeline import DataPipeline, prepare_data


class WalkForwardAnalyzer:
    """
    Walk-Forward 分析器
    
    将数据分为:
    - In-Sample (IS): 参数优化期
    - Out-of-Sample (OOS): 验证期
    
    滚动窗口执行
    """
    
    def __init__(self, 
                 config: BacktestConfig = None,
                 train_periods: int = 90,    # 样本内周期数
                 test_periods: int = 30,      # 样本外周期数
                 step_periods: int = 15):    # 滚动步长
        """
        Args:
            config: 回测配置
            train_periods: 样本内数据点数
            test_periods: 样本外数据点数
            step_periods: 滚动步长
        """
        self.config = config or BacktestConfig()
        self.train_periods = train_periods
        self.test_periods = test_periods
        self.step_periods = step_periods
        
        self.pipeline = DataPipeline()
        self.results: List[Dict] = []
    
    def run(self, 
            data: pd.DataFrame, 
            strategy,
            indicators: List[str] = None,
            validate: bool = True) -> Dict:
        """
        运行 Walk-Forward 分析
        
        Args:
            data: 原始数据
            strategy: 策略实例
            indicators: 需要添加的技术指标
            validate: 是否验证数据
            
        Returns:
            分析结果字典
        """
        # 数据预处理
        if validate:
            df = self.pipeline.process(data)
            is_valid, errors = self.pipeline.validate_ohlcv(df)
            if not is_valid:
                print(f"⚠️ 数据验证警告: {errors}")
        else:
            df = data.copy()
        
        # 添加指标
        if indicators:
            df = self.pipeline.add_indicators(df, indicators)
        
        # 检查数据量
        min_required = self.train_periods + self.test_periods
        if len(df) < min_required:
            return {
                'error': f'数据量不足: {len(df)} < {min_required}',
                'windows': []
            }
        
        # 滚动窗口
        windows = []
        start = 0
        
        while start + self.train_periods + self.test_periods <= len(df):
            # 分割数据
            train_end = start + self.train_periods
            test_end = train_end + self.test_periods
            
            train_df = df.iloc[start:train_end].copy()
            test_df = df.iloc[train_end:test_end].copy()
            
            # 在样本外数据上回测
            bt = Backtester(self.config)
            
            try:
                result = bt.run(test_df, strategy)
                
                windows.append({
                    'train_start': start,
                    'train_end': train_end - 1,
                    'test_start': train_end,
                    'test_end': test_end - 1,
                    'result': result,
                })
                
                print(f"  窗口 [{train_end}~{test_end-1}]: "
                      f"收益={result.get('total_return', 0):.2%}, "
                      f"夏普={result.get('sharpe_ratio', 0):.2f}")
                
            except Exception as e:
                print(f"  窗口 [{train_end}~{test_end-1}] 失败: {e}")
                windows.append({
                    'train_start': start,
                    'train_end': train_end - 1,
                    'test_start': train_end,
                    'test_end': test_end - 1,
                    'error': str(e),
                })
            
            start += self.step_periods
        
        # 聚合统计
        valid_results = [w['result'] for w in windows if 'result' in w]
        
        if valid_results:
            returns = [r['total_return'] for r in valid_results]
            drawdowns = [r['max_drawdown'] for r in valid_results]
            sharpes = [r['sharpe_ratio'] for r in valid_results]
            
            summary = {
                'windows': windows,
                'window_count': len(windows),
                'valid_windows': len(valid_results),
                'avg_total_return': float(np.mean(returns)),
                'std_total_return': float(np.std(returns)),
                'avg_max_drawdown': float(np.mean(drawdowns)),
                'avg_sharpe_ratio': float(np.mean(sharpes)),
                'win_rate': len([r for r in returns if r > 0]) / len(returns),
                'best_return': float(max(returns)),
                'worst_return': float(min(returns)),
            }
        else:
            summary = {
                'windows': windows,
                'window_count': len(windows),
                'valid_windows': 0,
                'error': 'No valid windows completed'
            }
        
        self.results = windows
        return summary
    
    def save_results(self, filepath: str):
        """保存结果到文件"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        return filepath


def run_walkforward(symbol: str = "BTCUSDT", 
                    interval: str = "4h",
                    start_date: str = None,
                    end_date: str = None,
                    capital: float = 10000):
    """
    便捷运行函数
    
    Args:
        symbol: 交易对
        interval: K线周期
        start_date: 开始日期
        end_date: 结束日期
        capital: 初始资金
    """
    from data_manager import DataManager
    
    dm = DataManager()
    
    # 默认最近2年
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=730)
    
    # 获取数据
    print(f"📊 获取数据: {symbol} {interval}")
    df = dm.get_binance_klines(
        symbol=symbol,
        interval=interval,
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d')
    )
    
    if df is None or len(df) < 200:
        print("❌ 数据获取失败或数据量不足")
        return None
    
    # 策略
    from light_strategy import generate_signal, calculate_indicators
    
    class LightStrategy:
        def get_name(self): return 'LightStrategy'
        
        def generate_signals(self, data):
            # 使用 light_strategy 的逻辑
            signals = []
            for i in range(len(data)):
                if i < 50:
                    signals.append(0)
                else:
                    df_slice = data.iloc[:i+1].copy()
                    signal = generate_signal(df_slice)
                    signals.append(1 if signal.get('signal') == 'BUY' else -1 if signal.get('signal') == 'SELL' else 0)
            return pd.Series(signals, index=data.index)
    
    # 配置
    config = BacktestConfig(
        initial_capital=capital,
        symbol=symbol,
        commission=0.001,
        slippage=0.0005,
    )
    
    # 运行
    analyzer = WalkForwardAnalyzer(
        config=config,
        train_periods=180,   # 样本内 30天 (4h*180=30天)
        test_periods=60,    # 样本外 10天
        step_periods=30,    # 步长 5天
    )
    
    print(f"\n🚀 开始 Walk-Forward 分析")
    print(f"   数据量: {len(df)}")
    print(f"   样本内: {analyzer.train_periods} 周期")
    print(f"   样本外: {analyzer.test_periods} 周期")
    print(f"   步长: {analyzer.step_periods} 周期")
    
    result = analyzer.run(df, LightStrategy(), indicators=['rsi', 'macd'])
    
    # 输出结果
    print(f"\n📈 Walk-Forward 结果:")
    print(f"   窗口数: {result.get('window_count', 0)}")
    print(f"   有效窗口: {result.get('valid_windows', 0)}")
    
    if 'avg_total_return' in result:
        print(f"   平均收益: {result['avg_total_return']:.2%}")
        print(f"   平均回撤: {result['avg_max_drawdown']:.2%}")
        print(f"   平均夏普: {result['avg_sharpe_ratio']:.2f}")
        print(f"   胜率: {result['win_rate']:.1%}")
    
    # 保存
    output = f"/root/.openclaw/workspace/quant/quant/logs/walkforward_{symbol}_{interval}.json"
    analyzer.save_results(output)
    print(f"\n✅ 结果已保存: {output}")
    
    return result


# 主函数
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Walk-Forward 分析')
    parser.add_argument('--symbol', default='BTCUSDT', help='交易对')
    parser.add_argument('--interval', default='4h', help='K线周期')
    parser.add_argument('--capital', type=float, default=10000, help='初始资金')
    
    args = parser.parse_args()
    
    run_walkforward(
        symbol=args.symbol,
        interval=args.interval,
        capital=args.capital
    )
