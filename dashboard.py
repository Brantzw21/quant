"""
Web Dashboard - 回测结果可视化
运行: python3 dashboard.py
访问: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, request
import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# 模拟数据（实际可以对接真实数据）
def get_backtest_data():
    """获取回测数据"""
    return {
        'strategy': 'RSI Strategy',
        'period': '2024-01-01 to 2026-02-27',
        'initial_capital': 100000,
        'final_capital': 125000,
        'total_return': 25.0,
        'sharpe': 1.2,
        'max_drawdown': 8.5,
        'win_rate': 58.0,
        'trades': 45,
        'equity': [float(100000 + i*125) for i in range(200)],
        'benchmark': [float(100000 + i*80) for i in range(200)],
        'returns': [float(x) for x in np.random.randn(199) * 2],
        'drawdown': [float(abs(i*0.05)) for i in range(200)]
    }

# HTML模板
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quant Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; color: #00d4ff; }
        .container { padding: 20px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .metric-card { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-value { font-size: 28px; font-weight: bold; color: #00d4ff; }
        .metric-label { font-size: 14px; color: #888; margin-top: 5px; }
        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .chart-card { background: #16213e; padding: 20px; border-radius: 10px; }
        .chart-title { font-size: 16px; margin-bottom: 15px; color: #00d4ff; }
        .nav { display: flex; gap: 10px; }
        .nav a { color: #888; text-decoration: none; padding: 8px 16px; border-radius: 5px; }
        .nav a:hover, .nav a.active { background: #0f3460; color: #00d4ff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Quant Dashboard</h1>
        <div class="nav">
            <a href="/" class="active">Backtest</a>
            <a href="#">Live</a>
            <a href="#">Settings</a>
        </div>
    </div>
    
    <div class="container">
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{{ data.total_return }}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ data.sharpe }}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ data.max_drawdown }}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ data.win_rate }}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ data.trades }}</div>
                <div class="metric-label">Total Trades</div>
            </div>
        </div>
        
        <div class="chart-grid">
            <div class="chart-card">
                <div class="chart-title">Equity Curve</div>
                <canvas id="equityChart"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">Drawdown</div>
                <canvas id="drawdownChart"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">Returns Distribution</div>
                <canvas id="returnsChart"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">Monthly Returns</div>
                <canvas id="monthlyChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        const data = {{ data_json | safe }};
        
        // Equity Chart
        new Chart(document.getElementById('equityChart'), {
            type: 'line',
            data: {
                labels: data.equity.map((_, i) => i),
                datasets: [
                    { label: 'Strategy', data: data.equity, borderColor: '#00d4ff', fill: false, tension: 0.1 },
                    { label: 'Benchmark', data: data.benchmark, borderColor: '#666', borderDash: [5,5], fill: false }
                ]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#888' } } }, scales: { x: { ticks: { color: '#666' } }, y: { ticks: { color: '#666' } } }
        });
        
        // Drawdown Chart
        new Chart(document.getElementById('drawdownChart'), {
            type: 'line',
            data: {
                labels: data.drawdown.map((_, i) => i),
                datasets: [{ label: 'Drawdown', data: data.drawdown, borderColor: '#ff6b6b', backgroundColor: 'rgba(255,107,107,0.2)', fill: true }]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#888' } } }, scales: { x: { ticks: { color: '#666' } }, y: { ticks: { color: '#666' } } }
        });
        
        // Returns Distribution
        new Chart(document.getElementById('returnsChart'), {
            type: 'bar',
            data: {
                labels: data.returns.map((_, i) => i),
                datasets: [{ label: 'Returns', data: data.returns, backgroundColor: '#4ecdc4' }]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#888' } } }, scales: { x: { ticks: { color: '#666' } }, y: { ticks: { color: '#666' } } }
        });
        
        // Monthly Returns
        new Chart(document.getElementById('monthlyChart'), {
            type: 'bar',
            data: {
                labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
                datasets: [{ label: '2024', data: [2.1, -1.5, 3.2, 1.8, -0.5, 2.5, 1.2, 3.5, -0.8, 2.0, 1.5, 3.0], backgroundColor: '#00d4ff' }]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#888' } } }, scales: { x: { ticks: { color: '#666' } }, y: { ticks: { color: '#666' } } }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    data = get_backtest_data()
    return render_template_string(HTML, data=data, data_json=json.dumps(data))

@app.route('/api/data')
def api_data():
    return jsonify(get_backtest_data())

@app.route('/api/equity')
def api_equity():
    data = get_backtest_data()
    return jsonify({
        'strategy': data['equity'],
        'benchmark': data['benchmark']
    })

if __name__ == '__main__':
    print("="*50)
    print("Quant Dashboard")
    print("="*50)
    print("Open: http://localhost:5000")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=False)
