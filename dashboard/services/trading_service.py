"""
交易服务模块
提供交易相关的数据获取逻辑
"""

import os
import json
import random
from typing import Dict, List
from datetime import datetime, timedelta

DATA_DIR = "/root/.openclaw/workspace/quant/quant"
TRADES_FILE = os.path.join(DATA_DIR, "logs/trades.json")
SIGNAL_FILE = os.path.join(DATA_DIR, "data/last_signal.json")


def load_json(fn: str, default=None) -> dict:
    if default is None:
        default = {}
    if os.path.exists(fn):
        try:
            return json.load(open(fn))
        except:
            pass
    return default


def get_positions(account_type: str = 'binance_simulate') -> List[Dict]:
    """获取持仓"""
    # 兼容旧版前端参数
    if account_type == 'simulate':
        account_type = 'binance_simulate'
    elif account_type == 'real':
        account_type = 'binance_real'
    
    random.seed(40)
    
    if account_type == 'binance_simulate':
        return [
            {
                "symbol": "BTCUSDT",
                "position": 0.022,
                "entry_price": 67500,
                "current_price": 68350,
                "pnl": round(random.uniform(-500, 1500), 2),
                "pnl_percent": round(random.uniform(-3, 8), 2),
                "margin": 500,
                "leverage": 3
            }
        ]
    elif account_type in ['a_stock_simulate', 'us_stock_simulate', 'binance_real']:
        return []
    
    return []


def get_orders() -> List[Dict]:
    """获取订单/成交记录"""
    trades = load_json(TRADES_FILE, [])
    
    if not trades:
        # 生成模拟数据
        random.seed(41)
        return [
            {
                "id": "1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "price": 67500,
                "volume": 0.022,
                "time": "2026-03-07 10:00:00",
                "status": "FILLED"
            },
            {
                "id": "2", 
                "symbol": "BTCUSDT",
                "side": "SELL",
                "price": 68000,
                "volume": 0.010,
                "time": "2026-03-07 14:30:00",
                "status": "FILLED"
            }
        ]
    
    return trades


def get_signals() -> Dict:
    """获取信号"""
    return load_json(SIGNAL_FILE, {
        "signal": "HOLD",
        "reason": "No clear signal",
        "timestamp": datetime.now().isoformat()
    })


def get_strategies() -> List[Dict]:
    """获取策略列表"""
    return [
        {
            "name": "robust_rsi",
            "display_name": "稳健RSI策略",
            "params": {
                "rsi_period": 5,
                "rsi_overbought": 75,
                "rsi_oversold": 25
            },
            "enabled": True
        },
        {
            "name": "dual_ma_rsi",
            "display_name": "双均线RSI策略",
            "params": {
                "fast_ma": 5,
                "slow_ma": 20,
                "rsi_period": 14
            },
            "enabled": False
        },
        {
            "name": "breakout",
            "display_name": "趋势突破策略",
            "params": {
                "lookback": 20,
                "atr_multiplier": 2
            },
            "enabled": False
        }
    ]


def get_factors() -> Dict:
    """获取因子数据"""
    random.seed(45)
    
    return {
        "rsi": round(random.uniform(20, 80), 2),
        "ma5": round(random.uniform(65000, 70000), 2),
        "ma20": round(random.uniform(64000, 69000), 2),
        "atr": round(random.uniform(500, 2000), 2),
        "bb_upper": round(random.uniform(68000, 72000), 2),
        "bb_lower": round(random.uniform(64000, 66000), 2),
        "volume": round(random.uniform(1000, 5000), 2),
        "timestamp": datetime.now().isoformat()
    }
