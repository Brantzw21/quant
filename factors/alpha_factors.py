"""
因子库 - Alpha Factors
======================

常见Alpha因子:
- 动量因子
- 价值因子
- 质量因子
- 成长因子
- 波动率因子

参考: WorldQuant, Quantopian

作者: AI量化系统
"""

import numpy as np
import pandas as pd
from typing import Union, List, Dict


# ==================== 基础因子 ====================

def returns(data: Union[pd.Series, List], period: int = 1) -> float:
    """收益率"""
    if isinstance(data, list):
        data = pd.Series(data)
    return (data.iloc[-1] / data.iloc[-period-1]) - 1


def log_returns(data: Union[pd.Series, List]) -> pd.Series:
    """对数收益率"""
    if isinstance(data, list):
        data = pd.Series(data)
    return np.log(data / data.shift(1))


# ==================== 动量因子 ====================

def momentum(data: Union[pd.Series, List], period: int = 20) -> float:
    """动量因子: 过去N天收益率"""
    if isinstance(data, list):
        data = pd.Series(data)
    return data.iloc[-1] / data.iloc[-period] - 1


def acceleration(data: Union[pd.Series, List], short: int = 10, long: int = 20) -> float:
    """加速度因子: 短期动量 - 长期动量"""
    if isinstance(data, list):
        data = pd.Series(data)
    
    short_mom = momentum(data, short)
    long_mom = momentum(data, long)
    
    return short_mom - long_mom


def reversal(data: Union[pd.Series, List], period: int = 5) -> float:
    """反转因子: 过去N天负收益"""
    return -momentum(data, period)


# ==================== 波动率因子 ====================

def volatility(data: Union[pd.Series, List], period: int = 20) -> float:
    """波动率因子: 过去N天收益率标准差年化"""
    if isinstance(data, list):
        data = pd.Series(data)
    
    rets = data.pct_change().dropna()
    
    if len(rets) < period:
        return 0
    
    vol = rets[-period:].std() * np.sqrt(252)
    return vol


def downside_volatility(data: Union[pd.Series, List], period: int = 20) -> float:
    """下行波动率"""
    if isinstance(data, list):
        data = pd.Series(data)
    
    rets = data.pct_change().dropna()
    
    if len(rets) < period:
        return 0
    
    negative_returns = rets[rets < 0]
    
    if len(negative_returns) == 0:
        return 0
    
    return negative_returns[-period:].std() * np.sqrt(252)


def beta(data: Union[pd.Series, List], benchmark: Union[pd.Series, List], 
         period: int = 60) -> float:
    """贝塔因子"""
    if isinstance(data, list):
        data = pd.Series(data)
    if isinstance(benchmark, list):
        benchmark = pd.Series(benchmark)
    
    stock_returns = data.pct_change().dropna()
    bench_returns = benchmark.pct_change().dropna()
    
    if len(stock_returns) < period:
        return 1
    
    # 对齐
    min_len = min(len(stock_returns), len(bench_returns), period)
    
    stock_rets = stock_returns[-min_len:]
    bench_rets = bench_returns[-min_len:]
    
    covariance = np.cov(stock_rets, bench_rets)[0][1]
    bench_var = np.var(bench_rets)
    
    if bench_var == 0:
        return 1
    
    return covariance / bench_var


# ==================== 价值因子 ====================

def pe_ratio(price: float, earnings: float) -> float:
    """市盈率"""
    if earnings == 0:
        return 0
    return price / earnings


def pb_ratio(price: float, book_value: float) -> float:
    """市净率"""
    if book_value == 0:
        return 0
    return price / book_value


def ps_ratio(price: float, sales: float) -> float:
    """市销率"""
    if sales == 0:
        return 0
    return price / sales


def dividend_yield(price: float, dividend: float) -> float:
    """股息率"""
    if price == 0:
        return 0
    return dividend / price


# ==================== 质量因子 ====================

def roe(net_income: float, equity: float) -> float:
    """净资产收益率"""
    if equity == 0:
        return 0
    return net_income / equity


def roa(net_income: float, assets: float) -> float:
    """资产收益率"""
    if assets == 0:
        return 0
    return net_income / assets


def gross_margin(revenue: float, cost: float) -> float:
    """毛利率"""
    if revenue == 0:
        return 0
    return (revenue - cost) / revenue


def debt_ratio(total_debt: float, total_assets: float) -> float:
    """资产负债率"""
    if total_assets == 0:
        return 0
    return total_debt / total_assets


def current_ratio(current_assets: float, current_liabilities: float) -> float:
    """流动比率"""
    if current_liabilities == 0:
        return 0
    return current_assets / current_liabilities


# ==================== 成长因子 ====================

def revenue_growth(current_revenue: float, previous_revenue: float) -> float:
    """营收增长率"""
    if previous_revenue == 0:
        return 0
    return (current_revenue - previous_revenue) / previous_revenue


def earnings_growth(current_earnings: float, previous_earnings: float) -> float:
    """盈利增长率"""
    if previous_earnings == 0:
        return 0
    return (current_earnings - previous_earnings) / previous_earnings


# ==================== 成交量因子 ====================

def volume_momentum(volume: Union[pd.Series, List], period: int = 20) -> float:
    """成交量动量"""
    if isinstance(volume, list):
        volume = pd.Series(volume)
    
    if len(volume) < period:
        return 0
    
    return volume.iloc[-1] / volume.iloc[-period] - 1


def volume_ma_ratio(volume: Union[pd.Series, List], period: int = 20) -> float:
    """成交量/均量"""
    if isinstance(volume, list):
        volume = pd.Series(volume)
    
    if len(volume) < period:
        return 1
    
    current = volume.iloc[-1]
    ma = volume[-period:].mean()
    
    if ma == 0:
        return 1
    
    return current / ma


def amihud_illiquidity(returns: Union[pd.Series, List], 
                       volume: Union[pd.Series, List]) -> float:
    """Amihud非流动性因子"""
    if isinstance(returns, list):
        returns = pd.Series(returns)
    if isinstance(volume, list):
        volume = pd.Series(volume)
    
    rets = returns.dropna()
    vols = volume.dropna()
    
    if len(rets) == 0 or len(vols) == 0:
        return 0
    
    # 对齐
    min_len = min(len(rets), len(vols))
    rets = rets[-min_len:]
    vols = vols[-min_len:]
    
    # 非流动性 = |收益| / 成交量
    illiq = np.abs(rets) / vols
    
    return illiq.mean()


# ==================== 复合因子 ====================

def sharpe_factor(returns: Union[pd.Series, List], period: int = 60) -> float:
    """夏普因子"""
    if isinstance(returns, list):
        returns = pd.Series(returns)
    
    rets = returns.pct_change().dropna()
    
    if len(rets) < period:
        return 0
    
    period_rets = rets[-period:]
    
    mean_ret = period_rets.mean()
    std_ret = period_rets.std()
    
    if std_ret == 0:
        return 0
    
    return (mean_ret / std_ret) * np.sqrt(252)


def sortino_factor(returns: Union[pd.Series, List], period: int = 60) -> float:
    """索提诺因子"""
    if isinstance(returns, list):
        returns = pd.Series(returns)
    
    rets = returns.pct_change().dropna()
    
    if len(rets) < period:
        return 0
    
    period_rets = rets[-period:]
    downside = period_rets[period_rets < 0]
    
    if len(downside) == 0:
        return 0
    
    mean_ret = period_rets.mean()
    downside_std = downside.std()
    
    if downside_std == 0:
        return 0
    
    return (mean_ret / downside_std) * np.sqrt(252)


def calmar_factor(returns: Union[pd.Series, List], 
                peak: float, 
                period: int = 60) -> float:
    """卡尔玛因子"""
    if isinstance(returns, list):
        returns = pd.Series(returns)
    
    rets = returns.pct_change().dropna()
    
    if len(rets) < period or peak == 0:
        return 0
    
    # 累计收益
    cumulative = (1 + rets).cumprod()
    
    # 最大回撤
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    
    if max_dd == 0:
        return 0
    
    # 年化收益
    annual_return = (cumulative.iloc[-1] ** (252/period)) - 1
    
    return annual_return / abs(max_dd)


# ==================== 因子组合 ====================

def compute_factors(price: Union[pd.Series, List],
                  volume: Union[pd.Series, List] = None,
                  benchmark: Union[pd.Series, List] = None,
                  fundamentals: Dict = None) -> Dict:
    """
    计算所有因子
    
    Returns:
        dict of factor_name: value
    """
    factors = {}
    
    # 价格数据
    if isinstance(price, list):
        price = pd.Series(price)
    
    # 动量因子
    factors['momentum_5'] = momentum(price, 5)
    factors['momentum_20'] = momentum(price, 20)
    factors['momentum_60'] = momentum(price, 60)
    factors['acceleration'] = acceleration(price)
    
    # 波动率因子
    factors['volatility_20'] = volatility(price, 20)
    factors['volatility_60'] = volatility(price, 60)
    factors['downside_vol'] = downside_volatility(price, 20)
    
    # 贝塔
    if benchmark is not None:
        factors['beta_60'] = beta(price, benchmark, 60)
    
    # 成交量因子
    if volume is not None:
        factors['volume_momentum'] = volume_momentum(volume, 20)
        factors['volume_ratio'] = volume_ma_ratio(volume, 20)
    
    # 基本面因子
    if fundamentals:
        factors['pe'] = fundamentals.get('pe', 0)
        factors['pb'] = fundamentals.get('pb', 0)
        factors['roe'] = fundamentals.get('roe', 0)
        factors['roa'] = fundamentals.get('roa', 0)
    
    return factors


# ==================== 使用示例 ====================

if __name__ == "__main__":
    import random
    
    # 模拟价格数据
    price = [100]
    for i in range(200):
        price.append(price[-1] * (1 + random.uniform(-0.02, 0.025)))
    price = pd.Series(price)
    
    volume = [random.randint(1000000, 5000000) for _ in range(200)]
    volume = pd.Series(volume)
    
    # 计算因子
    print("因子计算:")
    print(f"  动量20天: {momentum(price, 20):.2%}")
    print(f"  波动率20天: {volatility(price, 20):.2%}")
    print(f"  成交量动量: {volume_momentum(volume, 20):.2%}")
    print(f"  夏普因子: {sharpe_factor(price, 60):.2f}")
