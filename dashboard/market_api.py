#!/usr/bin/env python3
"""
多市场 Dashboard API
实时监控所有市场的行情、信号、持仓
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quant-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 数据缓存
MARKET_DATA = {
    'crypto': {},
    'astock': {},
    'us_stock': {}
}

SIGNALS = {}
ACCOUNT_DATA = {}


def get_crypto_data():
    """获取数字货币数据"""
    try:
        from config import API_KEY, SECRET_KEY, TESTNET
        from binance.client import Client
        
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        data = {}
        
        for symbol in symbols:
            try:
                ticker = client.get_symbol_ticker(symbol=symbol)
                klines = client.get_klines(symbol=symbol, interval="1h", limit=50)
                
                # 计算RSI
                closes = [float(k[4]) for k in klines]
                import numpy as np
                rsi = calculate_rsi(closes)
                
                data[symbol] = {
                    'price': float(ticker['price']),
                    'change_24h': get_price_change(symbol),
                    'volume_24h': get_volume(symbol),
                    'rsi': rsi,
                    'trend': 'bullish' if closes[-1] > np.mean(closes[-20:]) else 'bearish',
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
        
        return data
    except Exception as e:
        print(f"数字货币数据获取失败: {e}")
        return {}


def get_price_change(symbol):
    """获取24小时价格变化"""
    try:
        from config import API_KEY, SECRET_KEY, TESTNET
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        ticker = client.get_ticker(symbol=symbol)
        return float(ticker['priceChangePercent'])
    except:
        return 0


def get_volume(symbol):
    """获取24小时成交量"""
    try:
        from config import API_KEY, SECRET_KEY, TESTNET
        from binance.client import Client
        client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        
        ticker = client.get_ticker(symbol=symbol)
        return float(ticker['volume'])
    except:
        return 0


def calculate_rsi(closes, period=14):
    """计算RSI"""
    if len(closes) < period + 1:
        return 50
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def get_astock_data():
    """获取A股数据"""
    try:
        import baostock as bs
        
        lg = bs.login()
        if lg.error_code != '0':
            return {}
        
        indexes = [
            ('sh.000001', '上证指数'),
            ('sh.000300', '沪深300'),
            ('sz.399001', '深证成指'),
            ('sz.399006', '创业板指')
        ]
        
        data = {}
        
        for code, name in indexes:
            rs = bs.query_history_k_data_plus(
                code,
                'date,code,open,high,low,close,volume',
                start_date=(datetime.now().replace(hour=0, minute=0, second=0)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d'),
                frequency='d'
            )
            
            while rs.error_code == '0' and rs.next():
                row = rs.get_row_data()
                if len(row) >= 7:
                    data[code] = {
                        'name': name,
                        'close': float(row[6]) if row[6] else 0,
                        'change': 0,  # 需要昨日数据计算
                        'volume': float(row[5]) if row[5] else 0,
                        'timestamp': datetime.now().isoformat()
                    }
        
        bs.logout()
        return data
    except Exception as e:
        print(f"A股数据获取失败: {e}")
        return {}


def get_usstock_data():
    """获取美股数据"""
    try:
        import yfinance as yf
        
        symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL']
        data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2]
                    change = (current - previous) / previous * 100
                    
                    data[symbol] = {
                        'price': round(current, 2),
                        'change': round(change, 2),
                        'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
        
        return data
    except Exception as e:
        print(f"美股数据获取失败: {e}")
        return {}


def get_portfolio_summary():
    """获取组合摘要"""
    # 这里应该从 portfolio_risk.py 获取
    return {
        'total_value': 0,
        'positions': [],
        'daily_pnl': 0,
        'total_pnl': 0
    }


# ==================== API 路由 ====================

@app.route('/api/market/crypto')
def api_crypto():
    """数字货币行情"""
    return jsonify(MARKET_DATA.get('crypto', {}))


@app.route('/api/market/astock')
def api_astock():
    """A股行情"""
    return jsonify(MARKET_DATA.get('astock', {}))


@app.route('/api/market/usstock')
def api_usstock():
    """美股行情"""
    return jsonify(MARKET_DATA.get('us_stock', {}))


@app.route('/api/market/all')
def api_all_markets():
    """所有市场行情"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'markets': MARKET_DATA,
        'signals': SIGNALS,
        'portfolio': get_portfolio_summary()
    })


@app.route('/api/signals')
def api_signals():
    """交易信号"""
    return jsonify(SIGNALS)


@app.route('/api/portfolio')
def api_portfolio():
    """组合状态"""
    return jsonify(get_portfolio_summary())


# ==================== WebSocket ====================

def background_task():
    """后台数据更新"""
    while True:
        try:
            # 更新各市场数据
            MARKET_DATA['crypto'] = get_crypto_data()
            MARKET_DATA['astock'] = get_astock_data()
            MARKET_DATA['us_stock'] = get_usstock_data()
            
            # 推送到前端
            socketio.emit('market_update', {
                'timestamp': datetime.now().isoformat(),
                'markets': MARKET_DATA
            })
            
        except Exception as e:
            print(f"后台任务错误: {e}")
        
        socketio.sleep(10)  # 10秒更新一次


@socketio.on('connect')
def handle_connect():
    print('Dashboard client connected')
    emit('connected', {'status': 'ok'})


# 启动后台任务
threading.Thread(target=background_task, daemon=True).start()


# ==================== 启动 ====================

if __name__ == '__main__':
    print("=" * 50)
    print("多市场 Dashboard API")
    print("端口: 5001")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
