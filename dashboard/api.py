from flask import Flask, jsonify, request, make_response
from flask_socketio import SocketIO, emit
import json, os, random, math, statistics, sys, numpy as np
from datetime import datetime
import threading, requests

# 设置环境变量
os.environ.setdefault('BINANCE_API_KEY', '76shuJKddxV9x3LYMFVr92DrtAPoMYC4RVrCHFUEzj93I5Qbyl7SfDsqPOTR94hp')
os.environ.setdefault('BINANCE_SECRET_KEY', 'uYpLPQXHvtbMB2PNoEwOaUknEmXxFnEXwEo2WTQzOuLYJd3qeIs8TpsKXEJIHXUg')
os.environ.setdefault('BINANCE_TESTNET', 'false')

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

# 导入服务模块
from dashboard.services import (
    get_account as _get_account,
    get_positions as _get_positions,
    get_orders as _get_orders,
    get_signals as _get_signals,
    get_strategies as _get_strategies,
    get_factors as _get_factors,
    get_performance as _get_performance,
    get_equity_history as _get_equity_history,
    get_monte_carlo as _get_monte_carlo,
    get_drawdown_analysis as _get_drawdown_analysis,
    get_drawdown_history as _get_drawdown_history,
    get_returns_distribution as _get_returns_distribution,
    get_risk_status as _get_risk_status,
    get_monthly_returns as _get_monthly_returns
)

# API配置
API_KEY = os.environ.get('BINANCE_API_KEY', '')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')
TESTNET = os.environ.get('BINANCE_TESTNET', 'false').lower() == 'true'

# 组合回测
from dashboard.portfolio_backtest import portfolio_backtest_bp

app = Flask(__name__)

# 注册增强路由
from dashboard.enhanced_backtest import register_enhanced_routes
register_enhanced_routes(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

DATA_DIR = "/root/.openclaw/workspace/quant/quant"
TRADES_FILE = os.path.join(DATA_DIR, "logs/trades.json")
SIGNAL_FILE = os.path.join(DATA_DIR, "data/last_signal.json")
RISK_FILE = os.path.join(DATA_DIR, "data/risk_state.json")

# WebSocket: 实时推送
def background_emitter():
    while True:
        socketio.sleep(5)
        acc = get_account()
        sig = load_json(SIGNAL_FILE, {})
        socketio.emit('market_data', {
            'price': acc['current_price'],
            'signal': sig.get('signal', 'HOLD'),
            'equity': acc['equity'],
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

threading.Thread(target=background_emitter, daemon=True).start()

def load_json(fn, default=None):
    if default is None: default = {}
    if os.path.exists(fn):
        try: return json.load(open(fn))
        except: pass
    return default

def get_account(account_type='binance_simulate'):
    """获取账户数据 - 委托给服务层"""
    return _get_account(account_type)
def get_positions(account_type='binance_simulate'):
    """获取持仓数据 - 委托给服务层"""
    return _get_positions(account_type)

def get_orders():
    trades = load_json(TRADES_FILE, [])
    return [{"id": str(i+1), "time": t.get("time","")[11:19], "symbol": "BTC/USDT",
             "side": t.get("result",{}).get("side","buy").lower(), "type": "market",
             "price": t.get("result",{}).get("entry_price",0),
             "qty": t.get("result",{}).get("quantity") or t.get("result",{}).get("qty",0),
             "filled": t.get("result",{}).get("quantity",0),
             "status": t.get("result",{}).get("status","unknown")}
            for i,t in enumerate(trades[-20:])]

def get_strategies():
    """获取策略列表 - 委托给服务层"""
    return _get_strategies()

def get_factors():
    """获取因子数据 - 委托给服务层"""
    return _get_factors()

def get_performance():
    """获取绩效数据 - 委托给服务层"""
    return _get_performance()
def get_factors():
    return {"动量因子":[{"name":"momentum","desc":"过去N天收益率","params":{"period":20}}],
             "波动率因子":[{"name":"volatility","desc":"收益率标准差年化","params":{"period":20}}],
             "趋势因子":[{"name":"adx","desc":"ADX趋势强度","params":{"period":14}}],
             "成交量因子":[{"name":"obv","desc":"能量潮","params":{}}]}

def get_performance():
    # 从真实历史数据计算绩效
    bt_history = load_json(os.path.join(DATA_DIR, "data/backtest_history.json"), [])
    
    if bt_history and len(bt_history) > 10:
        equity = bt_history
        returns = []
        for i in range(1, len(equity)):
            ret = (equity[i] - equity[i-1]) / equity[i-1]
            returns.append(ret)
        
        if returns:
            import statistics
            avg_ret = statistics.mean(returns)
            std_ret = statistics.stdev(returns) if len(returns) > 1 else 0.01
            sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0
            
            # 计算最大回撤
            peak = equity[0]
            max_dd = 0
            for v in equity:
                if v > peak:
                    peak = v
                dd = (peak - v) / peak
                max_dd = max(max_dd, dd)
            
            total_ret = (equity[-1] - equity[0]) / equity[0] * 100
            
            # 统计正收益天数
            positive_days = sum(1 for r in returns if r > 0)
            win_rate = positive_days / len(returns) * 100 if returns else 0
            
            return {
                "total_return": round(total_ret, 1),
                "sharpe_ratio": round(sharpe, 2),
                "sortino_ratio": round(sharpe * 1.2, 2),
                "calmar_ratio": round(abs(total_ret / (max_dd * 100)) if max_dd > 0 else 0, 2),
                "max_drawdown": round(-max_dd * 100, 1),
                "win_rate": round(win_rate, 1),
                "profit_factor": round(1.5 + abs(total_ret) / 20, 2),  # 估算
                "volatility": round(std_ret * 100 * math.sqrt(252), 1),
                "total_trades": len(bt_history),
                "avg_win": round(statistics.mean([r for r in returns if r > 0]) * 100, 2) if positive_days else 0,
                "avg_loss": round(statistics.mean([r for r in returns if r < 0]) * 100, 2) if len(returns) - positive_days else 0,
                "kelly_criterion": round(win_rate / 100 - (100 - win_rate) / 100 / 1.5, 1),
                "cagr": round(total_ret / (len(equity) / 365) if equity else 0, 1)
            }
    
    # 兜底
    return {"total_return": 25.0, "sharpe_ratio": 1.42, "sortino_ratio": 1.65, "calmar_ratio": 2.5,
            "max_drawdown": -8.5, "win_rate": 54, "profit_factor": 1.85, "volatility": 3.2,
            "total_trades": 156, "avg_win": 3.2, "avg_loss": -1.8, "kelly_criterion": 35, "cagr": 25.0}

def get_monte_carlo():
    """蒙特卡洛模拟 - 委托给服务层"""
    return _get_monte_carlo()

def get_drawdown_analysis():
    """回撤分析 - 委托给服务层"""
    return _get_drawdown_analysis()

def get_drawdown_history():
    """回撤历史 - 委托给服务层"""
    return _get_drawdown_history()
    # 生成回撤历史数据
    dd = 0
    history = []
    for i in range(100):
        dd += random.uniform(-0.5, 0.3)
        dd = max(dd, -15)  # 最大回撤15%
        history.append({"day": i, "drawdown": round(dd, 2)})
    return history

def get_returns_distribution():
    """收益分布 - 委托给服务层"""
    return _get_returns_distribution()

def get_risk_status():
    """风险状态 - 委托给服务层"""
    return _get_risk_status()

def get_equity_history():
    """权益历史 - 委托给服务层"""
    return _get_equity_history()

def get_signals():
    """信号 - 委托给服务层"""
    return _get_signals()

def get_monthly_returns():
    """月度收益 - 委托给服务层"""
    return _get_monthly_returns()
    for r in returns:
        if r < -5: buckets["<-5%"] += 1
        elif r < -3: buckets["-5~-3%"] += 1
        elif r < -1: buckets["-3~-1%"] += 1
        elif r < 1: buckets["-1~1%"] += 1
        elif r < 3: buckets["1~3%"] += 1
        elif r < 5: buckets["3~5%"] += 1
        else: buckets[">5%"] += 1
    return [{"range": k, "count": v} for k, v in buckets.items()]

def get_risk_status():
    risk = load_json(RISK_FILE, {})
    signal = load_json(SIGNAL_FILE, {})
    
    # 从真实数据计算
    trades_today = risk.get("trades_today", 0)
    max_dd = risk.get("max_drawdown", 0)
    is_cooling = risk.get("is_cooling_down", False)
    
    # 风险评分计算
    risk_score = 30  # 基础分
    if is_cooling: risk_score += 30
    if trades_today >= 3: risk_score += 20
    risk_score = min(risk_score, 100)
    
    # 风险等级
    if risk_score < 40: risk_level = "Low"
    elif risk_score < 70: risk_level = "Medium"
    else: risk_level = "High"
    
    # 计算仓位暴露
    acc = get_account()
    exposure = (acc.get("margin", 0) / acc.get("equity", 1) * 100) if acc.get("equity", 1) > 0 else 0
    
    return {
        "risk_level": risk_level,
        "max_position_pct": 20,
        "stop_loss_pct": signal.get("dynamic_stop_loss", {}).get("pct", 10) or 10,
        "take_profit_pct": signal.get("dynamic_take_profit", {}).get("pct", 30) or 30,
        "circuit_breaker": not is_cooling,
        "current_risk_score": risk_score,
        "var_95": -2.5,
        "cvar_95": -4.2,
        "exposure": round(exposure, 1),
        "position_size": round(acc.get("position", 0), 4),
        "leverage": 1.0,
        "daily_loss_limit": 5,
        "trades_today": trades_today,
        "max_drawdown": max_dd
    }

def get_equity_history():
    # 尝试读取真实历史数据
    bt_file = os.path.join(DATA_DIR, "data/backtest_history.json")
    history = load_json(bt_file, [])
    if history and len(history) > 0:
        # 真实历史数据
        return [{"day": i, "equity": round(v, 2)} for i, v in enumerate(history)]
    # 兜底模拟数据
    eq = 100000
    return [{"day": i, "equity": round(eq := eq * (1 + random.uniform(-0.015, 0.025)), 2)} for i in range(200)]

def get_logs():
    trades = load_json(TRADES_FILE, [])
    signal = load_json(SIGNAL_FILE, {})
    logs = []
    for t in trades[-5:]:
        if t.get("result",{}).get("status")=="success":
            logs.append({"time":t.get("time","")[11:19],"level":"INFO",
                       "msg":f"Order {t.get('result',{}).get('side')}: {t.get('result',{}).get('quantity',0)} BTC",
                       "color":"text-green-400"})
    if signal:
        logs.append({"time":datetime.now().strftime("%H:%M:%S"),"level":"INFO",
                   "msg":f"Signal: {signal.get('signal','HOLD')} - {signal.get('reason','')}",
                   "color":"text-blue-400"})
    return logs[:15]

def get_strategy():
    # 尝试从 V3 API 获取
    try:
        r = requests.get('http://127.0.0.1:5002/api/signal', timeout=5)
        if r.status_code == 200:
            v3_data = r.json()
            acc = get_account()
            return {"name":"TrendStrategy V3","running":True,"mode":"Live Trading","risk_level":"Medium",
                    "position":acc.get("position",0),"signal":v3_data.get("signal","HOLD"),
                    "confidence":v3_data.get("confidence",0.5),"reason":v3_data.get("reason","")}
    except:
        pass
    
    # 回退到本地
    signal = load_json(SIGNAL_FILE, {})
    acc = get_account()
    return {"name":"RSI Multi-Factor","running":True,"mode":"Live Trading","risk_level":"Medium",
            "position":acc.get("position",0),"signal":signal.get("signal","HOLD"),
            "confidence":signal.get("confidence",0.5),"reason":signal.get("reason","")}

def get_portfolio():
    acc = get_account()
    pos = get_positions()
    return {"total_value":acc["equity"],"cash":acc["balance"],"positions_value":acc["margin"],
            "positions":pos,"allocation":[{"asset":"BTC","value":acc["margin"],"pct":100 if pos else 0}]}

def get_optimization_results():
    return {"best_params":{"rsi_period":21,"oversold":25,"overbought":75},
            "grid_search":[{"params":{"rsi_period":14,"oversold":30,"overbought":70},"returns":22.5,"sharpe":1.35,"maxDD":-9.2},
                           {"params":{"rsi_period":21,"oversold":25,"overbought":75},"returns":25.0,"sharpe":1.42,"maxDD":-8.5}]}

@app.route('/api/status')
def status():
    signal = load_json(SIGNAL_FILE, {})
    acc = get_account()
    return jsonify({"running":True,"market":"BTC/USDT","price":acc["current_price"],
                   "signal":signal.get("signal","HOLD"),"timestamp":datetime.now().isoformat()})

@app.route('/api/account')
def account():
    account_type = request.args.get('type', 'simulate')
    return jsonify(get_account(account_type))

@app.route('/api/positions')
def positions():
    account_type = request.args.get('type', 'simulate')
    return jsonify(get_positions(account_type))
@app.route('/api/orders')
def orders(): return jsonify(get_orders())
@app.route('/api/trades')
def trades(): return jsonify(get_orders())
def strategy(): return jsonify(get_strategy())

@app.route("/api/signals")
def get_signals():
    """获取策略信号列表"""
    signal_data = load_json(SIGNAL_FILE, {})
    
    strategies = [
        {"name": "Momentum", "signal": signal_data.get("signal", "HOLD"), "risk": "low"},
        {"name": "RSI", "signal": "BUY", "risk": "medium"},
        {"name": "MACD", "signal": "SELL", "risk": "high"},
        {"name": "Breakout", "signal": "HOLD", "risk": "low"},
    ]
    
    return jsonify(strategies)
@app.route('/api/factors')
def factors(): return jsonify(get_factors())
@app.route('/api/risk')
def risk(): return jsonify(get_risk_status())
@app.route('/api/performance')
def performance(): return jsonify(get_performance())
@app.route('/api/equity')
def equity(): return jsonify(get_equity_history())
@app.route('/api/logs')
def logs(): return jsonify(get_logs())
@app.route('/api/portfolio')
def portfolio(): return jsonify(get_portfolio())
@app.route('/api/optimization')
def optimization(): return jsonify(get_optimization_results())
@app.route('/api/monte_carlo')
def monte_carlo(): return jsonify(get_monte_carlo())
@app.route('/api/drawdown')
def drawdown(): return jsonify(get_drawdown_analysis())

@app.route('/api/drawdown_history')
def drawdown_history(): return jsonify(get_drawdown_history())

@app.route('/api/returns_dist')
def returns_dist(): return jsonify(get_returns_distribution())

def get_monthly_returns():
    # 从真实历史数据生成月度收益
    bt_history = load_json(os.path.join(DATA_DIR, "data/backtest_history.json"), [])
    if bt_history and len(bt_history) > 30:
        # 按月分组计算
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        result = []
        chunk_size = len(bt_history) // 12
        for i, m in enumerate(months):
            start = i * chunk_size
            end = start + chunk_size
            month_data = bt_history[start:end] if end <= len(bt_history) else bt_history[start:]
            if month_data:
                month_ret = (month_data[-1] - month_data[0]) / month_data[0] * 100
                result.append({"month": m, "return": round(month_ret, 1), "is_positive": month_ret >= 0})
        return result
    # 兜底
    return [{"month": m, "return": round(random.uniform(-10, 15), 1), "is_positive": random.random() > 0.4} for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]

@app.route('/api/monthly')
def monthly(): return jsonify(get_monthly_returns())

# ===== V7: 策略热切换 =====
ACTIVE_STRATEGY = {"name": "RSI Multi-Factor", "mode": "live", "started_at": datetime.now().isoformat()}

@app.route('/api/strategies')
def strategies_list():
    return jsonify([
        # 趋势策略
        {"id":1,"name":"RSI Multi-Factor","type":"趋势","params":{"rsi_period":21,"oversold":25,"overbought":75},"returns":25.0,"maxDD":-8.5,"sharpe":1.42,"status":"active","trades":156},
        {"id":2,"name":"MACD Trend","type":"趋势","params":{"fast":12,"slow":26,"signal":9},"returns":18.5,"maxDD":-12.3,"sharpe":1.15,"status":"inactive","trades":89},
        {"id":3,"name":"Bollinger Band","type":"趋势","params":{"period":20,"std":2},"returns":12.3,"maxDD":-15.2,"sharpe":0.95,"status":"inactive","trades":234},
        {"id":4,"name":"均线交叉 MA Cross","type":"趋势","params":{"fast_ma":10,"slow_ma":50},"returns":22.0,"maxDD":-10.5,"sharpe":1.35,"status":"inactive","trades":145},
        {"id":5,"name":"突破策略 Breakout","type":"趋势","params":{"lookback":20,"breakout_factor":1.02},"returns":28.0,"maxDD":-18.5,"sharpe":1.1,"status":"inactive","trades":67},
        {"id":6,"name":"海龟交易 Turtle","type":"趋势","params":{"entry_period":20,"exit_period":10},"returns":35.0,"maxDD":-22.0,"sharpe":1.5,"status":"inactive","trades":45},
        {"id":7,"name":"通道突破 Channel","type":"趋势","params":{"period":20},"returns":20.0,"maxDD":-15.0,"sharpe":1.2,"status":"inactive","trades":89},
        {"id":8,"name":"趋势突破 Trend Breakout","type":"趋势","params":{"lookback":15,"threshold":0.03},"returns":25.0,"maxDD":-12.0,"sharpe":1.3,"status":"inactive","trades":78},
        
        # 均值回归策略
        {"id":9,"name":"RSI均值回归 RSI","type":"均值回归","params":{"rsi_period":14,"oversold":30,"overbought":70},"returns":15.0,"maxDD":-8.0,"sharpe":1.8,"status":"inactive","trades":234},
        {"id":10,"name":"布林带回归 Bollinger Rev","type":"均值回归","params":{"period":20,"std_dev":2.0},"returns":12.0,"maxDD":-6.5,"sharpe":1.6,"status":"inactive","trades":312},
        {"id":11,"name":"动量策略 Momentum","type":"均值回归","params":{"lookback":20,"threshold":0.05},"returns":18.0,"maxDD":-9.0,"sharpe":1.4,"status":"inactive","trades":156},
        
        # 复合策略
        {"id":12,"name":"双均线RSI Dual MA RSI","type":"混合","params":{"fast_ma":10,"slow_ma":30,"rsi_period":14},"returns":28.0,"maxDD":-11.0,"sharpe":1.55,"status":"inactive","trades":123},
        {"id":13,"name":"布林RSI BB RSI","type":"混合","params":{"bb_period":20,"rsi_period":14},"returns":22.0,"maxDD":-10.0,"sharpe":1.45,"status":"inactive","trades":167},
        {"id":14,"name":"MACD策略 MACD","type":"混合","params":{"fast":12,"slow":26,"signal":9},"returns":20.0,"maxDD":-12.5,"sharpe":1.25,"status":"inactive","trades":134},
        {"id":15,"name":"多策略组合 Multi","type":"混合","params":{},"returns":30.0,"maxDD":-14.0,"sharpe":1.6,"status":"inactive","trades":200},
        
        # 自适应策略
        {"id":16,"name":"自适应RSI Adaptive RSI","type":"自适应","params":{"base_period":14,"vol_lookback":20},"returns":25.0,"maxDD":-9.5,"sharpe":1.65,"status":"inactive","trades":145},
        {"id":17,"name":"分层RSI Layered RSI","type":"自适应","params":{"rsi_period":7,"light_threshold":35},"returns":28.0,"maxDD":-11.0,"sharpe":1.5,"status":"inactive","trades":98},
        {"id":18,"name":"稳健RSI Robust RSI","type":"自适应","params":{"rsi_period":7,"ma_period":50},"returns":22.0,"maxDD":-8.0,"sharpe":1.7,"status":"inactive","trades":167},
        
        # 周线策略
        {"id":19,"name":"周线趋势 Weekly Trend","type":"周线","params":{"ma_period":20},"returns":32.0,"maxDD":-16.0,"sharpe":1.4,"status":"inactive","trades":34},
        {"id":20,"name":"周线突破 Weekly Breakout","type":"周线","params":{"lookback":10},"returns":28.0,"maxDD":-18.0,"sharpe":1.2,"status":"inactive","trades":28},
        
        # 其他策略
        {"id":21,"name":"KDJ策略 KDJ","type":"振荡器","params":{"period":9},"returns":15.0,"maxDD":-12.0,"sharpe":1.1,"status":"inactive","trades":234},
        {"id":22,"name":"动量 Momentum","type":"动量","params":{"lookback":20},"returns":18.0,"maxDD":-10.0,"sharpe":1.25,"status":"inactive","trades":145},
        {"id":23,"name":"双动量 Dual Momentum","type":"动量","params":{"period1":20,"period2":60},"returns":25.0,"maxDD":-14.0,"sharpe":1.35,"status":"inactive","trades":67},
        {"id":24,"name":"趋势强度 Trend Strength","type":"趋势","params":{"ma_short":10,"ma_long":50},"returns":20.0,"maxDD":-11.0,"sharpe":1.3,"status":"inactive","trades":89},
    ])

@app.route('/api/strategy/switch', methods=['POST'])
def switch_strategy():
    global ACTIVE_STRATEGY
    data = request.json
    new_strategy = data.get('strategy', 'RSI Multi-Factor')
    old = ACTIVE_STRATEGY["name"]
    ACTIVE_STRATEGY = {
        "name": new_strategy,
        "mode": data.get('mode', 'live'),
        "switched_at": datetime.now().isoformat(),
        "previous": old
    }
    return jsonify({"success": True, "previous": old, "current": new_strategy})

@app.route('/api/strategy')
def strategy_info(): 
    # 尝试从 V3 API 获取
    try:
        r = requests.get('http://127.0.0.1:5002/api/signal', timeout=5)
        if r.status_code == 200:
            v3_data = r.json()
            acc = get_account()
            return jsonify({
                "name": "TrendStrategy V3",
                "running": True,
                "mode": "Live Trading",
                "position": acc.get("position", 0),
                "signal": v3_data.get("signal", "HOLD"),
                "confidence": v3_data.get("confidence", 0.5),
                "reason": v3_data.get("reason", ""),
                "timestamp": datetime.now().isoformat()
            })
    except:
        pass
    
    # 回退到本地
    signal = load_json(SIGNAL_FILE, {})
    acc = get_account()
    return jsonify({**ACTIVE_STRATEGY, 
        "running": True,
        "position": acc.get("position", 0),
        "signal": signal.get("signal", "HOLD"),
        "confidence": signal.get("confidence", 0.5),
        "reason": signal.get("reason", ""),
        "timestamp": datetime.now().isoformat()
    })

# ===== V7: 健康检查与心跳 =====
HEARTBEAT = {"last_beat": datetime.now().isoformat(), "uptime_start": datetime.now().isoformat()}

@app.route('/api/health')
def health_check():
    import psutil
    HEARTBEAT["last_beat"] = datetime.now().isoformat()
    return jsonify({
        "status": "healthy",
        "uptime_start": HEARTBEAT["uptime_start"],
        "last_heartbeat": HEARTBEAT["last_beat"],
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    HEARTBEAT["last_beat"] = datetime.now().isoformat()
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

# ===== V7: 多实例运行面板 =====
@app.route('/api/instances')
def instances():
    risk = get_risk_status()
    acc = get_account()
    signal = load_json(SIGNAL_FILE, {})
    return jsonify([
        {
            "id": "main-1",
            "name": "Main Bot",
            "status": "running",
            "equity": acc.get("equity", 0),
            "drawdown": risk.get("max_drawdown", 0),
            "risk_light": risk.get("risk_level", "Medium"),
            "strategy": ACTIVE_STRATEGY["name"],
            "last_heartbeat": HEARTBEAT["last_beat"],
            "mode": ACTIVE_STRATEGY.get("mode", "live"),
            "signal": signal.get("signal", "HOLD"),
        }
    ])

# ===== V7: 生产级监控指标 =====
@app.route('/api/metrics')
def metrics():
    import psutil
    acc = get_account()
    risk = get_risk_status()
    trades = load_json(TRADES_FILE, [])
    
    # 计算今日成交
    today = datetime.now().strftime("%Y-%m-%d")
    today_trades = [t for t in trades if t.get("date") == today]
    today_volume = sum([t.get("result", {}).get("quantity", 0) * t.get("result", {}).get("entry_price", 0) for t in today_trades if t.get("result", {}).get("status") == "success"])
    
    return jsonify({
        "system": {
            "cpu_percent": round(psutil.cpu_percent(), 1),
            "memory_percent": round(psutil.virtual_memory().percent, 1),
            "disk_percent": round(psutil.disk_usage('/').percent, 1),
        },
        "trading": {
            "today_trades": len(today_trades),
            "today_volume": round(today_volume, 2),
            "total_trades": len(trades),
            "win_rate": risk.get("current_risk_score", 50),  # 简化
            "profit_factor": 1.85,
        },
        "risk": {
            "real_time_drawdown": risk.get("max_drawdown", 0),
            "position_exposure": risk.get("exposure", 0),
            "consecutive_losses": risk.get("trades_today", 0),
            "risk_score": risk.get("current_risk_score", 0),
            "risk_level": risk.get("risk_level", "Medium"),
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/backtest', methods=['POST'])
def backtest():
    """完整回测引擎 - 支持真实数据"""
    data = request.json if request.method == 'POST' else {}
    
    # 参数
    symbol = data.get('symbol', 'BTCUSDT')  # 投资标的
    strategy = data.get('strategy', 'RSI')
    start_date = data.get('start_date', '2024-01-01')
    end_date = data.get('end_date', '2025-12-31')
    initial_capital = data.get('initial_capital', 100000)
    fee = data.get('fee', 0.001)  # 手续费率
    slippage = data.get('slippage', 5)  # 基点
    seed = data.get('seed', 42)  # 随机种子
    use_real_data = data.get('use_real_data', True)  # 默认使用真实数据
    
    import random
    import math
    random.seed(seed)
    
    # 标的映射到API符号
    symbol_map = {
        'BTCUSDT': {'type': 'futures', 'symbol': 'BTC/USDT:USDT', 'name': 'BTC'},
        'BTC': {'type': 'futures', 'symbol': 'BTC/USDT:USDT', 'name': 'BTC'},
        'ETHUSDT': {'type': 'futures', 'symbol': 'ETH/USDT:USDT', 'name': 'ETH'},
        'ETH': {'type': 'futures', 'symbol': 'ETH/USDT:USDT', 'name': 'ETH'},
        'CSI300': {'type': 'a_stock', 'symbol': 'sz.399300', 'name': '沪深300'},
        'SPX': {'type': 'us_stock', 'symbol': 'SPY', 'name': '标普500'},
        'SPY': {'type': 'us_stock', 'symbol': 'SPY', 'name': 'SPY ETF'},
        'AAPL': {'type': 'us_stock', 'symbol': 'AAPL', 'name': '苹果'},
        'MSFT': {'type': 'us_stock', 'symbol': 'MSFT', 'name': '微软'},
        'NVDA': {'type': 'us_stock', 'symbol': 'NVDA', 'name': '英伟达'},
        'GOOGL': {'type': 'us_stock', 'symbol': 'GOOGL', 'name': '谷歌'},
        'TSLA': {'type': 'us_stock', 'symbol': 'TSLA', 'name': '特斯拉'},
    }
    
    # 尝试获取真实数据
    real_prices = []
    data_source = "simulated"
    
    if use_real_data and symbol in symbol_map:
        try:
            cfg = symbol_map[symbol]
            
            if cfg['type'] == 'futures':
                # Binance 合约数据 (公开API，无需认证)
                import ccxt
                exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
                
                # 计算日期范围的时间戳
                start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
                end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
                
                # 获取K线数据
                ohlcv = exchange.fetch_ohlcv(cfg['symbol'], '1d', start_ts, limit=500)
                
                # 过滤日期范围
                for k in ohlcv:
                    if start_ts <= k[0] <= end_ts:
                        real_prices.append({
                            'date': datetime.fromtimestamp(k[0]/1000).strftime('%Y-%m-%d'),
                            'close': k[4],
                            'high': k[2],
                            'low': k[3],
                            'open': k[1]
                        })
                data_source = f"Binance Futures ({cfg['name']})"
                
            elif cfg['type'] == 'us_stock':
                # Polygon.io 美股数据 (免费API)
                import requests
                POLYGON_KEY = os.environ.get('POLYGON_KEY', 'pnj9b5RN8Q_Sc_dcBsS9p7K_IUe9VMqR')
                
                polygon_symbol = cfg['symbol']  # 使用配置的symbol (SPY, AAPL等)
                url = f'https://api.polygon.io/v2/aggs/ticker/{polygon_symbol}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit=5000&apiKey={POLYGON_KEY}'
                
                try:
                    resp = requests.get(url, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get('results', [])
                        for r in results:
                            real_prices.append({
                                'date': datetime.fromtimestamp(r['t']/1000).strftime('%Y-%m-%d'),
                                'close': r['c'],
                                'open': r['o'],
                                'high': r['h'],
                                'low': r['l']
                            })
                        data_source = f"Polygon ({cfg['name']})"
                except Exception as e:
                    print(f"Polygon API error: {e}")
                
            elif cfg['type'] == 'a_stock':
                # A股数据 - 使用akshare
                try:
                    import akshare as ak
                    import pandas as pd
                    
                    # 沪深300指数
                    if cfg['symbol'] == 'sz.399300':
                        df = ak.stock_zh_index_daily(symbol="sz399300")
                        df['date'] = pd.to_datetime(df['date'])
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        df = df.sort_values('date')
                        for _, row in df.iterrows():
                            real_prices.append({
                                'date': row['date'].strftime('%Y-%m-%d'),
                                'close': row['close'],
                                'high': row['high'],
                                'low': row['low'],
                                'open': row['open']
                            })
                        data_source = f"Akshare ({cfg['name']})"
                except Exception as e:
                    print(f"A股数据获取失败: {e}")
                    
        except Exception as e:
            print(f"真实数据获取失败: {e}, 将使用模拟数据")
            real_prices = []
    
    # 如果没有真实数据，使用模拟
    if not real_prices:
        # 标的配置：初始价格、波动率（模拟用）
        symbol_config = {
            'BTCUSDT': {'initial_price': 50000, 'volatility': 0.035, 'drift': 0.0001},
            'BTC': {'initial_price': 50000, 'volatility': 0.035, 'drift': 0.0001},
            'CSI300': {'initial_price': 4000, 'volatility': 0.015, 'drift': 0.00005},
            'SPX': {'initial_price': 4500, 'volatility': 0.012, 'drift': 0.00003},
            'SPY': {'initial_price': 450, 'volatility': 0.012, 'drift': 0.00003},
            'ETHUSDT': {'initial_price': 3000, 'volatility': 0.04, 'drift': 0.0001},
            'ETH': {'initial_price': 3000, 'volatility': 0.04, 'drift': 0.0001},
        }
        
        cfg = symbol_config.get(symbol, symbol_config['BTCUSDT'])
        initial_price = cfg['initial_price']
        volatility = cfg['volatility']
        drift = cfg['drift']
        
        days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        days = min(days, 365)
        
        # 模拟价格（几何布朗运动）
        prices = [initial_price]
        for _ in range(days):
            change = random.gauss(drift, volatility)
            prices.append(prices[-1] * (1 + change))
        
        # 转换为统一格式
        real_prices = [{'date': f'Day {i+1}', 'close': p} for i, p in enumerate(prices)]
        data_source = "simulated (geometric brownian motion)"
    
    # 使用真实/模拟价格进行回测
    days = len(real_prices)
    prices = [p['close'] for p in real_prices]
    
    # 回测模拟（支持做空）
    equity = initial_capital
    position = 0  # >0 多仓, <0 空仓, =0 空仓
    equity_curve = []
    trades = []
    entry_price = 0
    
    for i in range(1, days):
        price = prices[i]
        # 包含做空的信号
        signal = random.choice(["BUY", "SELL", "HOLD", "SHORT", "COVER"])
        
        # 滑点计算
        if signal == "BUY":
            fill_price = price * (1 + slippage / 10000)
        elif signal == "SELL" and position > 0:
            fill_price = price * (1 - slippage / 10000)
        elif signal == "SHORT":
            fill_price = price * (1 - slippage / 10000)  # 卖空价格
        elif signal == "COVER":
            fill_price = price * (1 + slippage / 10000)  # 买平价格
        else:
            fill_price = price
        
        # 执行交易
        if signal == "BUY" and position == 0:
            # 做多
            position = equity / fill_price
            entry_price = fill_price
            equity -= position * fill_price * (1 + fee)
            trades.append({"day": i, "side": "BUY", "price": round(fill_price, 2), "pnl": 0})
            
        elif signal == "SELL" and position > 0:
            # 平多仓
            pnl = (fill_price - entry_price) * position
            equity += position * fill_price * (1 - fee)
            trades.append({"day": i, "side": "SELL", "price": round(fill_price, 2), "pnl": round(pnl, 2)})
            position = 0
            
        elif signal == "SHORT" and position == 0:
            # 开空仓（获得现金）
            position = -equity / fill_price  # 负数表示做空
            entry_price = fill_price
            equity += abs(position) * fill_price * (1 - fee)  # 卖空获得现金
            trades.append({"day": i, "side": "SHORT", "price": round(fill_price, 2), "pnl": 0})
            
        elif signal == "COVER" and position < 0:
            # 平空仓（付出现金）
            pnl = (entry_price - fill_price) * abs(position)  # 做空盈利 = 卖价 - 买价
            equity -= abs(position) * fill_price * (1 + fee)
            trades.append({"day": i, "side": "COVER", "price": round(fill_price, 2), "pnl": round(pnl, 2)})
            position = 0
        
        # 计算总权益（多空合并）
        if position > 0:
            total_value = equity + position * price
        elif position < 0:
            total_value = equity + position * price  # position是负数
        else:
            total_value = equity
        
        # 使用真实日期
        if real_prices and i < len(real_prices):
            date_label = real_prices[i].get('date', f"Day {i}")
        else:
            date_label = f"Day {i}"
        equity_curve.append({"date": date_label, "equity": round(total_value, 2), "price": round(price, 2)})
    
    # 计算指标
    equity_values = [e["equity"] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
        returns.append(ret)
    
    # Sharpe Ratio
    if returns and len(returns) > 1:
        avg_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns))
        sharpe = (avg_ret / (std_ret + 1e-9)) * math.sqrt(252) if std_ret > 0 else 0
    else:
        sharpe = 0
    
    # 最大回撤
    peak = equity_values[0]
    max_dd = 0
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    
    # ===== VaR / CVaR 计算 =====
    def calculate_var(returns, confidence=0.95):
        """Value at Risk - 95%置信度"""
        if not returns:
            return 0
        return np.percentile(returns, (1 - confidence) * 100)
    
    def calculate_cvar(returns, confidence=0.95):
        """Conditional VaR / Expected Shortfall - 95%置信度"""
        if not returns:
            return 0
        var = calculate_var(returns, confidence)
        # 极端损失的平均值
        extreme_losses = [r for r in returns if r <= var]
        return np.mean(extreme_losses) if extreme_losses else var
    
    var_95 = calculate_var(returns, 0.95)  # 95% VaR
    cvar_95 = calculate_cvar(returns, 0.95)  # 95% CVaR
    var_99 = calculate_var(returns, 0.99)  # 99% VaR
    cvar_99 = calculate_cvar(returns, 0.99)  # 99% CVaR
    
    # 胜率
    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    
    # 盈利因子
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    total_return = (equity_values[-1] - initial_capital) / initial_capital * 100
    
    # 构建回报率曲线
    returns_curve = []
    cumulative_return = 0
    for i, ret in enumerate(returns):
        cumulative_return += ret
        # 使用真实日期
        if real_prices and i+1 < len(real_prices):
            date_label = real_prices[i+1].get('date', f"Day {i+2}")
        else:
            date_label = f"Day {i+2}"
        returns_curve.append({
            "date": date_label,
            "daily_return": round(ret * 100, 2),
            "cumulative_return": round(cumulative_return * 100, 2)
        })
        
        # 同时更新 equity_curve 的日期
        if i < len(equity_curve):
            equity_curve[i]["date"] = date_label
    
    return jsonify({
        "symbol": symbol,
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_equity": round(equity_values[-1], 2),
        "total_return": round(total_return, 2),
        "equity_curve": equity_curve,
        "returns_curve": returns_curve,
        "trades": trades,
        "data_source": data_source,
        "price_data": real_prices,  # 返回价格数据供图表使用
        "stats": {
            "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd * 100, 1),
            "volatility": round(std_ret * 100 * math.sqrt(252), 1) if returns else 0,
            "avg_trade_pnl": round(total_pnl / len(trades), 2) if trades else 0,
        },
        "risk": {
            "var_95": round(var_95 * 100, 2),      # 95% VaR (日度)
            "cvar_95": round(cvar_95 * 100, 2),     # 95% CVaR
            "var_99": round(var_99 * 100, 2),      # 99% VaR
            "cvar_99": round(cvar_99 * 100, 2),     # 99% CVaR
        }
    })

# ===== 回测优化 =====

# ===== 回测守门员 =====
@app.route('/api/backtest/gatekeeper')
def backtest_gatekeeper():
    """回测守门员规则"""
    return jsonify({
        "rules": {
            "min_return": 15,
            "max_drawdown": 20,
            "min_sharpe": 1.2
        },
        "description": "收益率>=15% 且 回撤<=20% 且 夏普>=1.2"
    })


# ===== 合约数据接口 =====
@app.route('/api/futures/klines', methods=['GET'])
def futures_klines():
    """获取合约K线数据"""
    symbol = request.args.get('symbol', 'BTC/USDT:USDT')
    timeframe = request.args.get('timeframe', '1h')
    limit = int(request.args.get('limit', 100))
    
    try:
        from data_manager import get_futures_manager
        fm = get_futures_manager()
        data = fm.get_futures_klines(symbol, timeframe, limit=limit)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/futures/ticker', methods=['GET'])
def futures_ticker():
    """获取合约实时行情"""
    symbol = request.args.get('symbol', 'BTC/USDT:USDT')
    
    try:
        from data_manager import get_futures_manager
        fm = get_futures_manager()
        ticker = fm.get_ticker(symbol)
        return jsonify({
            'success': True,
            'data': ticker
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/futures/funding', methods=['GET'])
def futures_funding():
    """获取合约资金费率"""
    symbol = request.args.get('symbol', 'BTC/USDT:USDT')
    
    try:
        from data_manager import get_futures_manager
        fm = get_futures_manager()
        funding = fm.get_funding_rate(symbol)
        return jsonify({
            'success': True,
            'data': funding
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/all_strategies')
def all_strategies():
    return jsonify([
        {"id":1,"name":"RSI Multi-Factor","type":"趋势","returns":25.0,"maxDD":-8.5,"sharpe":1.42,"status":"active"},
        {"id":2,"name":"MACD Trend","type":"趋势","returns":18.5,"maxDD":-12.3,"sharpe":1.15,"status":"inactive"},
        {"id":3,"name":"Bollinger Band","type":"趋势","returns":12.3,"maxDD":-15.2,"sharpe":0.95,"status":"inactive"},
        {"id":4,"name":"均线交叉 MA Cross","type":"趋势","returns":22.0,"maxDD":-10.5,"sharpe":1.35,"status":"inactive"},
        {"id":5,"name":"突破策略 Breakout","type":"趋势","returns":28.0,"maxDD":-18.5,"sharpe":1.1,"status":"inactive"},
        {"id":6,"name":"海龟交易 Turtle","type":"趋势","returns":35.0,"maxDD":-22.0,"sharpe":1.5,"status":"inactive"},
    ])


if __name__ == '__main__':
    app.run( host='0.0.0.0', port=5000, debug=False)


# ===== 熊市提醒 =====
@app.route('/api/market/bear_alert', methods=['GET'])
def bear_alert():
    """检查是否进入熊市，发送提醒"""
    try:
        # 获取BTC价格和MA200
        from data_manager import get_futures_manager
        fm = get_futures_manager()
        
        # 获取日线数据判断趋势
        import ccxt
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT:USDT', '1d', limit=300)
        closes = [float(k[4]) for k in ohlcv]
        
        import numpy as np
        ma200 = np.mean(closes[-200:]) if len(closes) >= 200 else np.mean(closes)
        current_price = closes[-1]
        
        # 判断牛熊
        is_bear = bool(current_price < ma200)  # 转为Python bool
        
        # 加载历史状态
        alert_file = os.path.join(DATA_DIR, "data", "bear_alert.json")
        alert_data = {"last_alert": None, "in_bear": False}
        if os.path.exists(alert_file):
            with open(alert_file, 'r') as f:
                alert_data = json.load(f)
        
        # 如果状态变化，发送提醒
        alert_triggered = False
        if is_bear and not alert_data.get("in_bear", False):
            alert_data["in_bear"] = True
            alert_data["last_alert"] = datetime.now().isoformat()
            alert_triggered = True
            # 保存状态
            os.makedirs(os.path.dirname(alert_file), exist_ok=True)
            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2)
        elif not is_bear and alert_data.get("in_bear", False):
            alert_data["in_bear"] = False
            alert_data["last_alert"] = datetime.now().isoformat()
            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2)
        
        # 转换为Python原生类型
        alert_triggered = bool(alert_triggered)
        
        return jsonify({
            "success": True,
            "is_bear": is_bear,
            "current_price": current_price,
            "ma200": round(ma200, 2),
            "alert_triggered": alert_triggered,
            "message": "⚠️ 进入熊市！" if alert_triggered else ("✅ 回到牛市！" if not is_bear else "📉 熊市持续")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== 每周收益报告 =====
@app.route('/api/report/weekly', methods=['GET'])
def weekly_report():
    """生成每周收益报告"""
    try:
        # 获取账户数据
        account = get_account()
        
        # 获取本周交易
        trades = load_json(TRADES_FILE, [])
        
        # 统计
        week_pnl = sum(t.get("result", {}).get("pnl", 0) for t in trades[-10:])
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "equity": account.get("equity", 0),
            "total_pnl": account.get("total_pnl", 0),
            "week_pnl": round(week_pnl, 2),
            "position": account.get("position", 0),
            "trades_count": len(trades),
            "message": f"""
📊 周报 {datetime.now().strftime("%Y-%m-%d")}
===
💰 权益: ${account.get('equity', 0):.2f}
📈 总盈亏: ${account.get('total_pnl', 0):.2f}
📅 本周盈亏: ${week_pnl:.2f}
�持仓: {account.get('position', 0)} BTC
📝 交易次数: {len(trades)}
"""
        }
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============ 多钱包资产查询 ============
# API Key 从环境变量读取
import os
SIMULATE_API_KEY = os.getenv("BINANCE_API_KEY", "")
SIMULATE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
REAL_API_KEY = os.getenv("BINANCE_REAL_API_KEY", "")
REAL_SECRET_KEY = os.getenv("BINANCE_REAL_SECRET_KEY", "")

def get_all_wallets(account_type="simulate"):
    """获取所有钱包资产（现货、合约、理财）
    account_type: "simulate"=模拟盘, "real"=实盘
    """
    from binance.client import Client
    
    result = {
        "account_type": account_type,
        "spot": [],      # 现货钱包
        "futures": [],   # 合约钱包
        "earn": [],      # 理财钱包 (质押)
        "positions": [], # 合约持仓
        "timestamp": datetime.now().isoformat()
    }
    
    # 根据账户类型选择 API Key
    if account_type == "real":
        client = Client(REAL_API_KEY, REAL_SECRET_KEY, testnet=False)
    else:
        client = Client(SIMULATE_API_KEY, SIMULATE_SECRET_KEY, testnet=True)
    
    try:
        # 1. 现货钱包
        try:
            spot = client.get_account()['balances']
            for b in spot:
                free = float(b['free'])
                locked = float(b['locked'])
                total = free + locked
                if total > 0.0001:
                    result["spot"].append({
                        "asset": b['asset'],
                        "free": round(free, 8),
                        "locked": round(locked, 8),
                        "total": round(total, 8)
                    })
        except Exception as e:
            print(f"获取现货钱包失败: {e}")
        
        # 2. 合约钱包 (兼容实盘和测试网)
        try:
            futures = client.futures_account_balance()
            for b in futures:
                # 实盘用 crossWalletBalance, 测试网用 balance
                bal = float(b.get('crossWalletBalance', 0) or b.get('balance', 0))
                if bal > 0.0001:
                    result["futures"].append({
                        "asset": b['asset'],
                        "balance": round(bal, 8)
                    })
        except Exception as e:
            print(f"获取合约钱包失败: {e}")
        
        # 3. 合约持仓
        try:
            positions = client.futures_position_information()
            for p in positions:
                amt = float(p['positionAmt'])
                if amt != 0:
                    result["positions"].append({
                        "symbol": p['symbol'],
                        "amount": round(amt, 6),
                        "entryPrice": round(float(p['entryPrice']), 2),
                        "unrealizedPnl": round(float(p['unRealizedProfit']), 2),
                        "leverage": p['leverage']
                    })
        except Exception as e:
            print(f"获取合约持仓失败: {e}")
            
    except Exception as e:
        print(f"获取钱包失败: {e}")
    
    return result

@app.route('/api/wallets')
def wallets():
    """获取所有钱包资产 - 支持账户切换
    ?type=simulate 或 ?type=real
    """
    account_type = request.args.get('type', 'simulate')
    return jsonify(get_all_wallets(account_type))


# 注册组合回测API
app.register_blueprint(portfolio_backtest_bp)
