#!/usr/bin/env python3
"""
历史回测脚本兼容入口

说明：
- 旧版 run_backtest.py 已不再维护为独立回测引擎
- 当前默认请使用 unified_backtest.py 或 backtest_benchmark.py
"""

import sys

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from unified_backtest import main


if __name__ == '__main__':
    print('[compat] run_backtest.py -> unified_backtest.py')
    main()
