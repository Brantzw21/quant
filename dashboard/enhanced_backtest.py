"""
增强的回测API - 基于统一回测框架
"""
from datetime import datetime

from flask import jsonify, request
import pandas as pd
import sys

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from backtest_framework import Backtester, BacktestConfig, ParameterOptimizer
from unified_backtest import MARKETS, STRATEGIES, FunctionStrategy, get_data, to_dataframe


def get_markets():
    """获取支持的市场"""
    enriched = {}
    for key, meta in MARKETS.items():
        enriched[key] = {
            'name': meta['name'],
            'symbols': [{'code': s, 'name': s} for s in meta['examples']],
        }
    return jsonify(enriched)


def get_strategies():
    """获取支持的策略"""
    return jsonify([
        {'id': key, 'name': value[0], 'params': value[2]}
        for key, value in STRATEGIES.items()
    ])


def _build_strategy(strategy_key: str):
    desc, func, params = STRATEGIES[strategy_key]
    return desc, FunctionStrategy(desc, func, params)


def run_enhanced_backtest():
    """增强回测 - 直接调用统一主框架"""
    payload = request.json or {}
    market = payload.get('market', 'crypto')
    symbol = payload.get('symbol', 'BTCUSDT')
    strategy_key = payload.get('strategy', 'momentum')
    start_date = payload.get('start_date', '2024-01-01')
    end_date = payload.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    initial_capital = float(payload.get('initial_capital', 100000))
    fee = float(payload.get('fee', 0.001))
    slippage_bps = float(payload.get('slippage', 5))

    raw = get_data(market, symbol, start_date, end_date)
    df = to_dataframe(raw)
    if df.empty or len(df) < 60:
        return jsonify({'success': False, 'error': f'数据不足: {symbol}'})

    if strategy_key not in STRATEGIES:
        return jsonify({'success': False, 'error': f'未知策略: {strategy_key}'})

    desc, strategy = _build_strategy(strategy_key)
    config = BacktestConfig(
        initial_capital=initial_capital,
        commission=fee,
        slippage=slippage_bps / 10000.0,
        symbol=symbol,
    )
    backtester = Backtester(config)
    result = backtester.run(df, strategy)

    equity_curve = [
        {'date': ts, 'equity': round(eq, 2)}
        for ts, eq in zip(result['equity_timestamps'], result['equity_curve'])
    ]

    returns_curve = []
    prev = None
    cumulative = 0.0
    for ts, eq in zip(result['equity_timestamps'], result['equity_curve']):
        if prev is None:
            daily_ret = 0.0
        else:
            daily_ret = (eq - prev) / prev if prev else 0.0
        cumulative += daily_ret
        returns_curve.append({
            'date': ts,
            'daily_return': round(daily_ret * 100, 2),
            'cumulative_return': round(cumulative * 100, 2),
        })
        prev = eq

    price_data = []
    for i, row in df.iterrows():
        date_label = row.get('date', None)
        if not date_label:
            date_label = str(i)
        price_data.append({
            'date': date_label,
            'open': round(float(row['open']), 4),
            'high': round(float(row['high']), 4),
            'low': round(float(row['low']), 4),
            'close': round(float(row['close']), 4),
            'volume': round(float(row.get('volume', 0)), 4),
        })

    trades = []
    for trade in result['trades']:
        trades.append({
            'date': trade['time'],
            'side': trade['side'],
            'price': round(trade['price'], 4),
            'quantity': round(trade['quantity'], 6),
            'commission': round(trade['commission'], 4),
            'pnl': round(trade.get('pnl', 0.0), 4),
        })

    return jsonify({
        'success': True,
        'market': market,
        'symbol': symbol,
        'strategy': strategy_key,
        'strategy_name': desc,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'final_equity': round(result['final_equity'], 2),
        'total_return': round(result['total_return'] * 100, 2),
        'equity_curve': equity_curve,
        'returns_curve': returns_curve,
        'price_data': price_data,
        'data_source': f'unified_backtest:{market}',
        'trades': trades,
        'stats': {
            'total_trades': result['sell_trades'],
            'sharpe_ratio': round(result['sharpe_ratio'], 3),
            'max_drawdown': round(result['max_drawdown'] * 100, 2),
            'win_rate': round(result['win_rate'] * 100, 2),
            'profit_factor': round(result['profit_factor'], 3),
            'total_commission': round(result['total_commission'], 2),
            'total_slippage_cost': round(result['total_slippage_cost'], 2),
        }
    })


def optimize_backtest():
    payload = request.json or {}
    market = payload.get('market', 'crypto')
    symbol = payload.get('symbol', 'BTCUSDT')
    strategy_key = payload.get('strategy', 'momentum')
    start_date = payload.get('start_date', '2024-01-01')
    end_date = payload.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    initial_capital = float(payload.get('initial_capital', 100000))
    param_grid = payload.get('param_grid', {})

    raw = get_data(market, symbol, start_date, end_date)
    df = to_dataframe(raw)
    if df.empty or len(df) < 60:
        return jsonify({'success': False, 'error': f'数据不足: {symbol}'})
    if strategy_key not in STRATEGIES:
        return jsonify({'success': False, 'error': f'未知策略: {strategy_key}'})

    desc, func, default_params = STRATEGIES[strategy_key]
    merged_grid = param_grid or {k: [v] for k, v in default_params.items()} or {'period': [20]}

    class TunableFunctionStrategy(FunctionStrategy):
        def __init__(self, name, signal_func, params):
            super().__init__(name, signal_func, params)

    backtester = Backtester(BacktestConfig(initial_capital=initial_capital, symbol=symbol))
    optimizer = ParameterOptimizer(backtester)
    results = optimizer.grid_search(
        df,
        lambda **params: TunableFunctionStrategy(desc, func, params),
        merged_grid,
        top_n=min(20, max(1, len(list(merged_grid.keys())) * 5)),
    )

    return jsonify({
        'success': True,
        'strategy': strategy_key,
        'strategy_name': desc,
        'best_params': results[0]['params'] if results else {},
        'all_results': results,
        'total_combinations': int(__import__('math').prod(len(v) for v in merged_grid.values())),
    })


def walkforward_backtest():
    payload = request.json or {}
    market = payload.get('market', 'crypto')
    symbol = payload.get('symbol', 'BTCUSDT')
    strategy_key = payload.get('strategy', 'momentum')
    start_date = payload.get('start_date', '2024-01-01')
    end_date = payload.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    initial_capital = float(payload.get('initial_capital', 100000))
    train_size = int(payload.get('train_size', 120))
    test_size = int(payload.get('test_size', 30))
    step_size = int(payload.get('step_size', test_size))

    raw = get_data(market, symbol, start_date, end_date)
    df = to_dataframe(raw)
    if df.empty or len(df) < (train_size + test_size):
        return jsonify({'success': False, 'error': f'数据不足，至少需要 {train_size + test_size} 条'})
    if strategy_key not in STRATEGIES:
        return jsonify({'success': False, 'error': f'未知策略: {strategy_key}'})

    desc, strategy = _build_strategy(strategy_key)
    backtester = Backtester(BacktestConfig(initial_capital=initial_capital, symbol=symbol))
    wf = backtester.walk_forward(df, strategy, train_size=train_size, test_size=test_size, step_size=step_size)

    periods = []
    for idx, window in enumerate(wf['windows'], start=1):
        result = window['result']
        periods.append({
            'period': f'P{idx}',
            'train_range': [window['train_start'], window['train_end']],
            'test_range': [window['test_start'], window['test_end']],
            'test_return': round(result['total_return'] * 100, 2),
            'sharpe': round(result['sharpe_ratio'], 3),
            'max_drawdown': round(result['max_drawdown'] * 100, 2),
            'passed': bool(result['sharpe_ratio'] > 0 and result['max_drawdown'] < 0.2),
        })

    pass_ratio = (sum(1 for p in periods if p['passed']) / len(periods) * 100) if periods else 0
    return jsonify({
        'success': True,
        'strategy': strategy_key,
        'strategy_name': desc,
        'periods': periods,
        'window_count': wf['window_count'],
        'pass_ratio': round(pass_ratio, 2),
        'avg_total_return': round(wf['avg_total_return'] * 100, 2),
        'avg_max_drawdown': round(wf['avg_max_drawdown'] * 100, 2),
        'avg_sharpe_ratio': round(wf['avg_sharpe_ratio'], 3),
        'wf_score': 'PASS' if pass_ratio >= 60 else 'FAIL',
    })


# 注册路由
def register_enhanced_routes(app):
    """注册增强路由"""
    app.add_url_rule('/api/enhanced/markets', 'get_markets', get_markets, methods=['GET'])
    app.add_url_rule('/api/enhanced/strategies', 'get_strategies', get_strategies, methods=['GET'])
    app.add_url_rule('/api/enhanced/backtest', 'run_enhanced_backtest', run_enhanced_backtest, methods=['POST'])
    app.add_url_rule('/api/backtest/optimize', 'optimize_backtest', optimize_backtest, methods=['POST'])
    app.add_url_rule('/api/backtest/walkforward', 'walkforward_backtest', walkforward_backtest, methods=['POST'])

    @app.route('/api/enhanced/kline', methods=['GET'])
    def get_kline():
        market = request.args.get('market', 'a_stock')
        symbol = request.args.get('symbol', 'sz.399006')
        limit = int(request.args.get('limit', 100))
        raw = get_data(market, symbol, '2024-01-01', datetime.now().strftime('%Y-%m-%d'))
        df = to_dataframe(raw)
        if df.empty:
            return jsonify([])
        df = df.tail(limit).reset_index(drop=True)
        data = []
        for i, row in df.iterrows():
            data.append({
                'time': str(i),
                'open': round(float(row['open']), 4),
                'high': round(float(row['high']), 4),
                'low': round(float(row['low']), 4),
                'close': round(float(row['close']), 4),
                'volume': round(float(row.get('volume', 0)), 4),
            })
        return jsonify(data)
