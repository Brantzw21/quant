"""
Dashboard Services
"""
from .account_service import get_account, get_account_binance_simulate
from .trading_service import get_positions, get_orders, get_signals, get_strategies, get_factors
from .analysis_service import (
    get_performance,
    get_equity_history,
    get_monte_carlo,
    get_drawdown_analysis,
    get_drawdown_history,
    get_returns_distribution,
    get_risk_status,
    get_monthly_returns
)

__all__ = [
    'get_account',
    'get_account_binance_simulate',
    'get_positions',
    'get_orders',
    'get_signals',
    'get_strategies',
    'get_factors',
    'get_performance',
    'get_equity_history',
    'get_monte_carlo',
    'get_drawdown_analysis',
    'get_drawdown_history',
    'get_returns_distribution',
    'get_risk_status',
    'get_monthly_returns'
]
