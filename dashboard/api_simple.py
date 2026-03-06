#!/usr/bin/env python3
"""
简化的API服务器 - 只提供HTTP API，不包含WebSocket
"""
import os
import sys

# 设置环境变量
os.environ.setdefault('BINANCE_API_KEY', '76shuJKddxV9x3LYMFVr92DrtAPoMYC4RVrCHFUEzj93I5Qbyl7SfDsqPOTR94hp')
os.environ.setdefault('BINANCE_SECRET_KEY', 'uYpLPQXHvtbMB2PNoEwOaUknEmXxFnEXwEo2WTQzOuLYJd3qeIs8TpsKXEJIHXUg')
os.environ.setdefault('BINANCE_TESTNET', 'true')

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 导入必要的模块
from dashboard.api import (
    get_account, get_positions, get_trades, get_equity_curve,
    get_performance, get_logs, get_strategy, get_risk,
    get_drawdown_history, get_returns_dist, get_monthly_returns,
    get_all_strategies, get_metrics, get_instances, health_check,
    get_backtest_result, optimize_params, walk_forward_analysis,
    get_klines, get_ticker, get_funding_rate,
    all_strategies, switch_strategy,
    get_all_wallets
)

# 注册路由
@app.route('/api/account')
def account():
    return jsonify(get_account())

@app.route('/api/positions')
def positions():
    return jsonify(get_positions())

@app.route('/api/trades')
def trades():
    return jsonify(get_trades())

@app.route('/api/equity')
def equity():
    return jsonify(get_equity_curve())

@app.route('/api/performance')
def performance():
    return jsonify(get_performance())

@app.route('/api/logs')
def logs():
    return jsonify(get_logs())

@app.route('/api/strategy')
def strategy():
    return jsonify(get_strategy())

@app.route('/api/risk')
def risk():
    return jsonify(get_risk())

@app.route('/api/drawdown_history')
def drawdown_history():
    return jsonify(get_drawdown_history())

@app.route('/api/returns_dist')
def returns_dist():
    return jsonify(get_returns_dist())

@app.route('/api/monthly')
def monthly():
    return jsonify(get_monthly_returns())

@app.route('/api/strategies')
def strategies():
    return jsonify(get_all_strategies())

@app.route('/api/metrics')
def metrics():
    return jsonify(get_metrics())

@app.route('/api/instances')
def instances():
    return jsonify(get_instances())

@app.route('/api/health')
def health():
    return jsonify(health_check())

@app.route('/api/wallets')
def wallets():
    """获取所有钱包资产 - 支持账户切换"""
    account_type = request.args.get('type', 'simulate')
    return jsonify(get_all_wallets(account_type))

@app.route('/api/backtest', methods=['POST'])
def backtest():
    return jsonify(get_backtest_result(request.json))

@app.route('/api/backtest/optimize', methods=['POST'])
def backtest_optimize():
    return jsonify(optimize_params(request.json))

@app.route('/api/backtest/walkforward', methods=['POST'])
def backtest_walkforward():
    return jsonify(walk_forward_analysis(request.json))

@app.route('/api/futures/klines')
def futures_klines():
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 100))
    return jsonify(get_klines(symbol, interval, limit))

@app.route('/api/futures/ticker')
def futures_ticker():
    symbol = request.args.get('symbol', 'BTCUSDT')
    return jsonify(get_ticker(symbol))

@app.route('/api/futures/funding')
def futures_funding():
    symbol = request.args.get('symbol', 'BTCUSDT')
    return jsonify(get_funding_rate(symbol))

@app.route('/api/all_strategies')
def all_strategies_route():
    return jsonify(all_strategies())

@app.route('/api/strategy/switch', methods=['POST'])
def strategy_switch():
    return jsonify(switch_strategy(request.json))

@app.route('/api/status')
def status():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
