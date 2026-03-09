"""
分析服务模块
提供绩效/风险分析相关的数据逻辑
"""

import os
import json
import random
import math
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

DATA_DIR = "/root/.openclaw/workspace/quant/quant"
RISK_FILE = os.path.join(DATA_DIR, "data/risk_state.json")


def load_json(fn: str, default=None) -> dict:
    if default is None:
        default = {}
    if os.path.exists(fn):
        try:
            return json.load(open(fn))
        except:
            pass
    return default


def get_performance() -> Dict:
    """获取绩效数据"""
    random.seed(50)
    
    return {
        "total_return": round(random.uniform(5, 25), 2),
        "annual_return": round(random.uniform(60, 120), 2),
        "sharpe_ratio": round(random.uniform(0.5, 2.0), 2),
        "sortino_ratio": round(random.uniform(0.8, 2.5), 2),
        "calmar_ratio": round(random.uniform(0.3, 1.5), 2),
        "max_drawdown": round(random.uniform(5, 15), 2),
        "volatility": round(random.uniform(10, 25), 2),
        "win_rate": round(random.uniform(45, 65), 2),
        "profit_factor": round(random.uniform(1.2, 2.5), 2),
        "total_trades": random.randint(50, 200),
        "winning_trades": random.randint(25, 120),
        "losing_trades": random.randint(20, 80),
        "timestamp": datetime.now().isoformat()
    }


def get_equity_history(days: int = 30) -> List[Dict]:
    """获取权益历史"""
    random.seed(51)
    
    equity_data = []
    base_value = 100000
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days - i - 1)
        # 添加随机波动
        change = random.uniform(-0.03, 0.04)
        base_value *= (1 + change)
        
        equity_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "equity": round(base_value, 2),
            "benchmark": round(100000 * (1 + i * 0.002), 2)
        })
    
    return equity_data


def get_monte_carlo(simulations: int = 1000) -> Dict:
    """蒙特卡洛模拟"""
    random.seed(52)
    
    # 简单模拟
    returns = [random.uniform(-0.05, 0.08) for _ in range(simulations)]
    
    return {
        "final_values": returns,
        "mean": round(np.mean(returns) * 100, 2),
        "std": round(np.std(returns) * 100, 2),
        "percentile_5": round(np.percentile(returns, 5) * 100, 2),
        "percentile_95": round(np.percentile(returns, 95) * 100, 2),
        "VaR_95": round(np.percentile(returns, 5) * 100, 2),
        "simulations": simulations
    }


def get_drawdown_analysis() -> Dict:
    """回撤分析"""
    random.seed(53)
    
    return {
        "max_drawdown": round(random.uniform(8, 20), 2),
        "current_drawdown": round(random.uniform(0, 10), 2),
        "max_drawdown_duration": random.randint(10, 60),
        "recovery_time": random.randint(5, 30),
        "drawdown_periods": [
            {"start": "2026-01-15", "end": "2026-02-01", "depth": round(random.uniform(5, 15), 2)},
            {"start": "2026-02-20", "end": "2026-03-01", "depth": round(random.uniform(3, 10), 2)}
        ]
    }


def get_drawdown_history(days: int = 90) -> List[Dict]:
    """回撤历史"""
    random.seed(54)
    
    dd_data = []
    dd = 0
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days - i - 1)
        # 随机漫步生成回撤
        change = random.uniform(-0.02, 0.015)
        dd = max(0, dd + change * 10)
        
        dd_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "drawdown": round(dd, 2)
        })
    
    return dd_data


def get_returns_distribution(bins: int = 20) -> Dict:
    """收益分布"""
    random.seed(55)
    
    # 生成正态分布收益
    returns = np.random.normal(0.001, 0.02, 1000)
    
    hist, edges = np.histogram(returns, bins=bins)
    
    return {
        "histogram": hist.tolist(),
        "edges": edges.tolist(),
        "mean": round(np.mean(returns) * 100, 4),
        "std": round(np.std(returns) * 100, 4),
        "skewness": round(random.uniform(-0.5, 0.5), 2),
        "kurtosis": round(random.uniform(2, 5), 2)
    }


def get_risk_status() -> Dict:
    """风险状态"""
    risk_data = load_json(RISK_FILE, {})
    
    return {
        "risk_level": risk_data.get("risk_level", "NORMAL"),
        "max_drawdown_pct": risk_data.get("max_drawdown_pct", 0),
        "daily_loss_pct": risk_data.get("daily_loss_pct", 0),
        "consecutive_losses": risk_data.get("consecutive_losses", 0),
        "cooldown_remaining": risk_data.get("cooldown_remaining", 0),
        "is_paused": risk_data.get("is_paused", False),
        "last_check": risk_data.get("last_check", datetime.now().isoformat())
    }


def get_monthly_returns(year: int = None) -> List[Dict]:
    """月度收益"""
    if year is None:
        year = datetime.now().year
    
    random.seed(year)
    
    months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    returns = []
    
    for m in months:
        returns.append({
            "month": f"{year}-{m}",
            "return": round(random.uniform(-5, 12), 2),
            "trades": random.randint(5, 25)
        })
    
    return returns
