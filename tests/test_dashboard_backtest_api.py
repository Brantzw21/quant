import pandas as pd
from flask import Flask

from dashboard.enhanced_backtest import register_enhanced_routes


def create_app():
    app = Flask(__name__)
    register_enhanced_routes(app)
    return app


def test_backtest_optimize_endpoint(monkeypatch):
    app = create_app()
    client = app.test_client()

    def fake_get_data(market, symbol, start, end):
        return pd.DataFrame({
            'open': [100 + i for i in range(200)],
            'high': [101 + i for i in range(200)],
            'low': [99 + i for i in range(200)],
            'close': [100 + i for i in range(200)],
            'volume': [1000 for _ in range(200)],
        })

    monkeypatch.setattr('dashboard.enhanced_backtest.get_data', fake_get_data)

    resp = client.post('/api/backtest/optimize', json={
        'market': 'crypto',
        'symbol': 'BTCUSDT',
        'strategy': 'momentum',
        'param_grid': {'period': [10, 20]},
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['total_combinations'] == 2


def test_backtest_walkforward_endpoint(monkeypatch):
    app = create_app()
    client = app.test_client()

    def fake_get_data(market, symbol, start, end):
        return pd.DataFrame({
            'open': [100 + i for i in range(220)],
            'high': [101 + i for i in range(220)],
            'low': [99 + i for i in range(220)],
            'close': [100 + i for i in range(220)],
            'volume': [1000 for _ in range(220)],
        })

    monkeypatch.setattr('dashboard.enhanced_backtest.get_data', fake_get_data)

    resp = client.post('/api/backtest/walkforward', json={
        'market': 'crypto',
        'symbol': 'BTCUSDT',
        'strategy': 'momentum',
        'train_size': 120,
        'test_size': 40,
        'step_size': 40,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['window_count'] > 0
