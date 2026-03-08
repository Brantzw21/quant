"""
配置文件 - 从环境变量读取敏感信息
"""

import os

# API配置 - 从环境变量读取
API_KEY = os.getenv("BINANCE_API_KEY", "")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

# 实盘API配置 - 从环境变量读取
REAL_API_KEY = os.getenv("BINANCE_REAL_API_KEY", "")
REAL_SECRET_KEY = os.getenv("BINANCE_REAL_SECRET_KEY", "")

# Tushare配置 (可选)
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 交易配置
SYMBOL = os.getenv("QUANT_SYMBOL", "BTCUSDT")
LEVERAGE = int(os.getenv("QUANT_LEVERAGE", "3"))
POSITION_PCT = float(os.getenv("QUANT_POSITION_PCT", "0.2"))
MIN_TRADE_VALUE = float(os.getenv("QUANT_MIN_TRADE_VALUE", "100"))
MAX_POSITION_PCT = float(os.getenv("QUANT_MAX_POSITION_PCT", "0.5"))

# 风控配置
STOP_LOSS = float(os.getenv("QUANT_STOP_LOSS", "0.03"))
TAKE_PROFIT = float(os.getenv("QUANT_TAKE_PROFIT", "0.08"))
MAX_DAILY_TRADES = int(os.getenv("QUANT_MAX_DAILY_TRADES", "5"))
CONSECUTIVE_LOSS_LIMIT = int(os.getenv("QUANT_CONSECUTIVE_LOSS_LIMIT", "3"))
COOLDOWN_MINUTES = int(os.getenv("QUANT_COOLDOWN_MINUTES", "60"))

# 策略配置
INTERVALS = {
    "4h": 100,
    "1h": 50,
    "15m": 50
}

# 运行配置
CHECK_INTERVAL = 1800  # 30分钟

# 日志
LOG_FILE = "logs/trading.log"
LOG_DIR = "logs"

# ==================== 市场基准配置 ====================
MARKET_BENCHMARK = {
    "虚拟货币": {
        "name": "虚拟货币",
        "symbol": "BTCUSDT",
        "symbol_ccxt": "BTC/USDT",
        "benchmark": "BTC",
        "data_source": "binance",
        "intervals": {"4h": 100, "1h": 50, "15m": 50}
    },
    "A股": {
        "name": "沪深300",
        "symbol": "sh.000300",
        "benchmark": "沪深300指数",
        "data_source": "baostock",
        "intervals": {"1d": 250, "1w": 100}
    },
    "美股": {
        "name": "标普500",
        "symbol": "SPY",
        "benchmark": "S&P 500",
        "data_source": "yfinance",
        "intervals": {"1d": 252, "1w": 104}
    }
}

# 当前实盘市场
CURRENT_MARKET = "虚拟货币"

# 默认时间周期
DEFAULT_INTERVAL = "1h"
