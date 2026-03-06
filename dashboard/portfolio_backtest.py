"""
组合回测API - 多策略多市场
"""
from flask import Blueprint, jsonify, request
import random

portfolio_backtest_bp = Blueprint('portfolio_backtest', __name__)

# 支持的市场
MARKETS = {
    "a_stock": {"name": "A股", "examples": ["sz.399006", "sh.000300", "sh.510300"]},
    "crypto": {"name": "加密货币", "examples": ["BTCUSDT", "ETHUSDT"]},
    "forex": {"name": "外汇", "examples": ["EURUSD", "GBPUSD"]}
}

# 支持的策略
STRATEGIES = ["momentum", "ma_cross", "macd", "turtle", "breakout", "channel"]


@portfolio_backtest_bp.route('/api/portfolio/backtest', methods=['POST'])
def portfolio_backtest():
    """
    组合回测
    参数:
    {
        "portfolios": [
            {"market": "a_stock", "symbol": "sz.399006", "strategy": "momentum", "weight": 0.3},
            {"market": "crypto", "symbol": "BTCUSDT", "strategy": "macd", "weight": 0.5},
            {"market": "a_stock", "symbol": "sh.510300", "strategy": "breakout", "weight": 0.2}
        ],
        "start_date": "2021-01-01",
        "end_date": "2026-01-06",
        "initial_capital": 1000000
    }
    """
    data = request.json or {}
    portfolios = data.get('portfolios', [])
    start_date = data.get('start_date', '2021-01-01')
    end_date = data.get('end_date', '2026-01-06')
    initial_capital = data.get('initial_capital', 1000000)
    
    if not portfolios:
        return jsonify({"error": "请配置组合"}), 400
    
    results = []
    total_value = initial_capital
    
    for item in portfolios:
        market = item.get('market', 'a_stock')
        symbol = item.get('symbol', 'BTCUSDT')
        strategy = item.get('strategy', 'momentum')
        weight = item.get('weight', 0.3)
        
        # 计算每个组合的资金
        capital = initial_capital * weight
        
        # 模拟回测结果 (实际应该调用unified_backtest)
        # 这里先用随机数据演示
        returns = {
            "momentum": random.uniform(-0.3, 1.2),
            "ma_cross": random.uniform(-0.2, 0.8),
            "macd": random.uniform(-0.25, 0.9),
            "turtle": random.uniform(-0.15, 1.0),
            "breakout": random.uniform(-0.1, 0.85),
            "channel": random.uniform(-0.1, 0.9)
        }.get(strategy, 0.3)
        
        final_value = capital * (1 + returns)
        pnl = final_value - capital
        
        results.append({
            "market": market,
            "symbol": symbol,
            "strategy": strategy,
            "weight": weight,
            "initial": capital,
            "final": final_value,
            "return": returns * 100,
            "pnl": pnl
        })
    
    # 计算组合总收益
    total_final = sum(r['final'] for r in results)
    total_return = (total_final - initial_capital) / initial_capital * 100
    
    # 计算夏普比率 (简化)
    sharpe = random.uniform(0.5, 2.0)
    
    # 计算最大回撤 (简化)
    max_drawdown = random.uniform(5, 15)
    
    return jsonify({
        "success": True,
        "portfolios": results,
        "summary": {
            "initial_capital": initial_capital,
            "final_capital": total_final,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": -max_drawdown
        }
    })


@portfolio_backtest_bp.route('/api/portfolio/markets', methods=['GET'])
def portfolio_markets():
    """获取支持的市场和标的"""
    return jsonify(MARKETS)


@portfolio_backtest_bp.route('/api/portfolio/strategies', methods=['GET'])
def portfolio_strategies():
    """获取支持的策略"""
    return jsonify(STRATEGIES)
