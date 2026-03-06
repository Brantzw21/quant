'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
Date: 2026-02-24 17:32:59
LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditTime: 2026-02-24 17:33:01
FilePath: \quant\strategies\example.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
"""
策略模块使用示例
"""

from strategies import STRATEGY_REGISTRY, get_strategy, list_strategies
from strategies.backtest import run_backtest, run_dca_backtest, optimize_strategy
import baostock as bs
from datetime import datetime


# 1. 列出所有可用策略
print("=== 可用策略 ===")
for code, name in list_strategies():
    print(f"  {code}: {name}")


# 2. 获取策略配置
print("\n=== 获取策略 ===")
strategy = get_strategy("ma_cross")
print(f"名称: {strategy['name']}")
print(f"默认参数: {strategy['default_params']}")
print(f"参数网格: {strategy['param_grid']}")


# 3. 获取数据
print("\n=== 获取数据 ===")
lg = bs.login()
rs = bs.query_history_k_data_plus(
    "sh.000300", 
    "date,open,high,low,close,volume", 
    start_date="2021-02-01", 
    end_date="2026-02-24", 
    frequency="d"
)
data_list = []
while rs.next():
    data_list.append(rs.get_row_data())
bs.logout()

import pandas as pd
df = pd.DataFrame(data_list, columns=rs.fields)
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
data = df.to_dict('records')
print(f"数据: {len(data)} 天")


# 4. 运行回测
print("\n=== 运行回测 ===")
strategy = get_strategy("ma_cross")
result = run_backtest(data, strategy['signal_func'], strategy['default_params'])
print(f"策略: {strategy['name']}")
print(f"总收益: {result['total_return']:.2%}")
print(f"年化收益: {result['annual_return']:.2%}")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2%}")
print(f"交易次数: {result['trades']}")


# 5. 参数优化
print("\n=== 参数优化 ===")
result, params = optimize_strategy(
    data, 
    strategy['signal_func'], 
    strategy['param_grid'],
    strategy['name']
)
print(f"最优参数: {params}")
