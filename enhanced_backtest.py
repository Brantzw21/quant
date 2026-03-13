#!/usr/bin/env python3
"""
增强回测兼容层

说明：
- 项目默认主回测框架已统一到 backtest_framework.py
- 本文件保留旧名称，避免历史导入失效
- 如需增强成本模型，请直接使用 backtest_framework.Backtester + BacktestConfig
"""

import sys

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_framework import Backtester, BacktestConfig


class EnhancedBacktestEngine(Backtester):
    """兼容别名，底层直接复用统一主框架。"""

    def __init__(self, config: BacktestConfig = None):
        super().__init__(config or BacktestConfig())


__all__ = ['EnhancedBacktestEngine', 'BacktestConfig']


if __name__ == '__main__':
    print('EnhancedBacktestEngine 已兼容到 backtest_framework.Backtester')
