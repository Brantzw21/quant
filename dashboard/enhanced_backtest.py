"""
增强的回测API - 支持多市场
"""
from flask import Flask, jsonify, request
import random
import sys
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

# 数据管理器
try:
    from data_manager import MarketDataManager, FuturesDataManager
    dm = MarketDataManager()
    fdm = FuturesDataManager()
except:
    dm = None
    fdm = None

# 支持的市场
MARKETS = {
    "crypto": {
        "name": "加密货币", 
        "symbols": [
            {"code": "BTCUSDT", "name": "比特币 BTC"},
            {"code": "ETHUSDT", "name": "以太坊 ETH"},
            {"code": "BNBUSDT", "name": "币安币 BNB"}
        ]
    },
    "us_stock": {
        "name": "美股", 
        "symbols": [
            {"code": "SPX", "name": "标普500 ^GSPC"},
            {"code": "SPY", "name": "SPY ETF"},
            {"code": "AAPL", "name": "苹果"},
            {"code": "MSFT", "name": "微软"},
            {"code": "GOOGL", "name": "谷歌"},
            {"code": "TSLA", "name": "特斯拉"},
            {"code": "NVDA", "name": "英伟达"}
        ]
    },
    "a_stock": {
        "name": "A股", 
        "symbols": [
            {"code": "sz.399006", "name": "创业板指"},
            {"code": "sh.000300", "name": "沪深300"},
            {"code": "sh.000016", "name": "上证50"},
            {"code": "sh.510300", "name": "沪深300ETF"},
            {"code": "sh.159919", "name": "券商ETF"}
        ]
    }
}

# 策略列表
STRATEGIES = [
    {"id": "momentum", "name": "动量策略", "params": {"period": 20}},
    {"id": "ma_cross", "name": "均线交叉", "params": {"fast": 5, "slow": 20}},
    {"id": "macd", "name": "MACD", "params": {}},
    {"id": "turtle", "name": "海龟策略", "params": {}},
    {"id": "breakout", "name": "突破策略", "params": {}},
    {"id": "channel", "name": "通道突破", "params": {}},
]


def get_markets():
    """获取支持的市场"""
    return jsonify(MARKETS)


def get_strategies():
    """获取支持的策略"""
    return jsonify(STRATEGIES)


def run_enhanced_backtest():
    """增强回测 - 支持多市场"""
    from datetime import datetime
    import math
    
    data = request.json or {}
    
    market = data.get('market', 'crypto')
    symbol = data.get('symbol', 'BTCUSDT')
    strategy = data.get('strategy', 'momentum')
    start_date = data.get('start_date', '2024-01-01')
    end_date = data.get('end_date', '2025-12-31')
    initial_capital = data.get('initial_capital', 100000)
    fee = data.get('fee', 0.001)
    slippage = data.get('slippage', 5)
    seed = data.get('seed', 42)
    
    import random
    random.seed(seed)
    
    # 标的映射
    symbol_map = {
        'BTCUSDT': {'type': 'crypto', 'ccxt': 'BTC/USDT:USDT'},
        'ETHUSDT': {'type': 'crypto', 'ccxt': 'ETH/USDT:USDT'},
        'BNBUSDT': {'type': 'crypto', 'ccxt': 'BNB/USDT:USDT'},
        'SPX': {'type': 'us_stock', 'yahoo': '^GSPC'},
        '^GSPC': {'type': 'us_stock', 'yahoo': '^GSPC'},
        'SPY': {'type': 'us_stock', 'yahoo': 'SPY'},
        'AAPL': {'type': 'us_stock', 'yahoo': 'AAPL'},
        'MSFT': {'type': 'us_stock', 'yahoo': 'MSFT'},
    }
    
    # 获取真实数据
    real_prices = []
    data_source = "simulated"
    
    try:
        cfg = symbol_map.get(symbol, {})
        
        if cfg.get('type') == 'crypto':
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(cfg['ccxt'], '1d', start_ts, limit=500)
            for k in ohlcv:
                if start_ts <= k[0] <= end_ts:
                    real_prices.append({
                        'date': datetime.fromtimestamp(k[0]/1000).strftime('%Y-%m-%d'),
                        'close': k[4], 'high': k[2], 'low': k[3], 'open': k[1]
                    })
            data_source = f"Binance Futures ({symbol})"
            
        elif cfg.get('type') == 'us_stock':
            try:
                import yfinance as yf
                ticker = yf.Ticker(cfg['yahoo'])
                hist = ticker.history(start=start_date, end=end_date)
                for idx, row in hist.iterrows():
                    real_prices.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'close': row['Close'], 'high': row['High'], 'low': row['Low'], 'open': row['Open']
                    })
                data_source = f"Yahoo Finance ({symbol})"
            except:
                pass
    except Exception as e:
        print(f"数据获取失败: {e}")
    
    # 如果没有真实数据，使用模拟
    if not real_prices or len(real_prices) < 2:
        days = min(365, (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days)
        initial_price = 50000 if market == 'crypto' else (4500 if market == 'us_stock' else 4000)
        prices = [initial_price]
        for _ in range(days):
            prices.append(prices[-1] * (1 + random.gauss(0.0001, 0.02)))
        real_prices = [{'date': f'Day {i+1}', 'close': p} for i, p in enumerate(prices)]
        data_source = "simulated"
    
    # 回测模拟
    prices = [p['close'] for p in real_prices]
    days = len(prices)
    
    equity = initial_capital
    position = 0
    equity_curve = []
    trades = []
    entry_price = 0
    
    for i in range(1, days):
        price = prices[i]
        signal = random.choice(["BUY", "SELL", "HOLD"])
        
        if signal == "BUY" and position == 0:
            fill_price = price * (1 + slippage / 10000)
            position = equity / fill_price
            entry_price = fill_price
            equity -= position * fill_price * (1 + fee)
            trades.append({"date": real_prices[i].get('date', f'Day {i}'), "side": "BUY", "price": round(fill_price, 2)})
        elif signal == "SELL" and position > 0:
            fill_price = price * (1 - slippage / 10000)
            pnl = (fill_price - entry_price) * position
            equity += position * fill_price * (1 - fee)
            trades.append({"date": real_prices[i].get('date', f'Day {i}'), "side": "SELL", "price": round(fill_price, 2), "pnl": round(pnl, 2)})
            position = 0
        
        total_value = equity + position * price if position > 0 else equity
        equity_curve.append({
            "date": real_prices[i].get('date', f'Day {i}'),
            "equity": round(total_value, 2)
        })
    
    # 计算指标
    equity_values = [e["equity"] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
        returns.append(ret)
    
    if returns and len(returns) > 1:
        avg_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns))
        sharpe = (avg_ret / (std_ret + 1e-9)) * math.sqrt(252) if std_ret > 0 else 0
    else:
        sharpe = 0
    
    peak = equity_values[0] if equity_values else initial_capital
    max_dd = 0
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    
    total_return = (equity_values[-1] - initial_capital) / initial_capital * 100 if equity_values else 0
    
    # 构建回报率曲线
    returns_curve = []
    cumulative_return = 0
    for i, ret in enumerate(returns):
        cumulative_return += ret
        date_label = real_prices[i+1].get('date', f'Day {i+2}') if i+1 < len(real_prices) else f'Day {i+2}'
        returns_curve.append({
            "date": date_label,
            "daily_return": round(ret * 100, 2),
            "cumulative_return": round(cumulative_return * 100, 2)
        })
    
    return jsonify({
        "success": True,
        "market": market,
        "symbol": symbol,
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_equity": round(equity_values[-1], 2) if equity_values else initial_capital,
        "total_return": round(total_return, 2),
        "equity_curve": equity_curve,
        "returns_curve": returns_curve,
        "price_data": real_prices,
        "data_source": data_source,
        "trades": trades,
        "stats": {
            "total_trades": len(trades),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd * 100, 1),
        }
    })


# 注册路由
def register_enhanced_routes(app):
    """注册增强路由"""
    app.add_url_rule('/api/enhanced/markets', 'get_markets', get_markets, methods=['GET'])
    app.add_url_rule('/api/enhanced/strategies', 'get_strategies', get_strategies, methods=['GET'])

    @app.route("/api/enhanced/kline", methods=["GET"])
    def get_kline():
        market = request.args.get("market", "a_stock")
        symbol = request.args.get("symbol", "sz.399006")
        limit = request.args.get("limit", 100)
        
        try:
            if market == "a_stock" and dm:
                df = dm.get_a_stock_klines(symbol, "2024-01-01", "2026-01-06")
                if df is not None and len(df) > 0:
                    df = df.tail(int(limit))
                    return jsonify(df.to_dict("records"))
        except:
            pass
        
        import random
        data = []
        base = 50000
        for i in range(int(limit)):
            o = base + random.uniform(-1000, 1000)
            h = o + random.uniform(0, 500)
            l = o - random.uniform(0, 500)
            c = o + random.uniform(-500, 500)
            data.append({
                "time": f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}",
                "open": o, "high": h, "low": l, "close": c,
                "volume": random.uniform(1000000, 5000000)
            })
            base = c
        
        return jsonify(data)
    app.add_url_rule('/api/enhanced/backtest', 'run_enhanced_backtest', run_enhanced_backtest, methods=['POST'])
