"""
市场状态识别模块
识别: 趋势/震荡/牛市/熊市
"""
import numpy as np


def calculate_atr(high, low, close, period=14):
    """计算ATR (Average True Range)"""
    if len(high) < period + 1:
        return None
    
    tr = []
    for i in range(1, len(high)):
        h_l = high[i] - low[i]
        h_c = abs(high[i] - close[i-1])
        l_c = abs(low[i] - close[i-1])
        tr.append(max(h_l, h_c, l_c))
    
    atr = np.mean(tr[-period:])
    return atr


def detect_market_regime(prices, period=20):
    """
    检测市场状态
    返回: 'trend_up', 'trend_down', 'range', 'volatile'
    """
    if len(prices) < period:
        return 'unknown'
    
    prices = np.array(prices)
    
    # 计算趋势指标
    ma_short = np.mean(prices[-period//2:])
    ma_long = np.mean(prices[-period:])
    
    # 计算波动率
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)
    
    # 计算价格位置
    recent_high = np.max(prices[-period:])
    recent_low = np.min(prices[-period:])
    price_pos = (prices[-1] - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
    
    # 判断逻辑
    if volatility > 0.05:  # 高波动
        return 'volatile'
    
    if ma_short > ma_long * 1.02:  # 明显上涨趋势
        return 'trend_up'
    elif ma_short < ma_long * 0.98:  # 明显下跌趋势
        return 'trend_down'
    elif price_pos < 0.3 or price_pos > 0.7:  # 震荡边界
        return 'range'
    else:
        return 'neutral'


def get_dynamic_stop_loss(entry_price, atr, market_regime, multiplier=2):
    """
    根据ATR计算动态止损
    multiplier: ATR倍数 (通常2-3)
    """
    if atr is None:
        return entry_price * 0.97  # 默认3%止损
    
    atr_value = atr * multiplier
    
    if market_regime == 'trend_up':
        # 趋势中用更宽松的止损
        return entry_price - atr_value * 1.5
    elif market_regime == 'trend_down':
        return entry_price + atr_value * 1.5
    elif market_regime == 'volatile':
        # 高波动市场用更宽的止损
        return entry_price - atr_value * 3
    else:
        # 震荡市场用紧止损
        return entry_price - atr_value


def get_dynamic_take_profit(entry_price, atr, market_regime, risk_ratio=2):
    """
    根据ATR计算动态止盈
    risk_ratio: 风险回报比 (通常2-3)
    """
    if atr is None:
        return entry_price * 1.08  # 默认8%止盈
    
    atr_value = atr * risk_ratio
    
    if market_regime == 'trend_up':
        # 趋势中追求更大利润
        return entry_price + atr_value * 3
    elif market_regime == 'trend_down':
        return entry_price - atr_value * 3
    elif market_regime == 'volatile':
        return entry_price + atr_value * 2
    else:
        return entry_price + atr_value * 2


def calculate_trailing_stop(entry_price, current_price, atr, market_regime, stage=1):
    """
    移动止盈/止损 - 根据盈利阶段调整止损价
    
    Args:
        entry_price: 开仓价格
        current_price: 当前价格
        atr: ATR值
        market_regime: 市场状态
        stage: 盈利阶段 (1=初期的50%, 2=中期的70%, 3=高位的90%)
    
    Returns:
        float: 移动止损价格
    """
    if atr is None:
        return None
    
    profit_pct = (current_price - entry_price) / entry_price * 100
    
    if profit_pct < 20:
        # 盈利<20%: 止损移到成本价
        return entry_price * 1.01  # 1%利润
    elif profit_pct < 50:
        # 盈利20-50%: 止损移到20%利润
        return entry_price * 1.20
    elif profit_pct < 100:
        # 盈利50-100%: 止损移到50%利润
        return entry_price * 1.50
    else:
        # 盈利>100%: 止损移到70%利润
        return entry_price * 1.70


def calculate_position_size(account_balance, risk_per_trade, entry_price, stop_loss_price):
    """
    根据风险计算仓位大小
    risk_per_trade: 每笔风险比例 (例如0.02表示2%)
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0
    
    risk_amount = account_balance * risk_per_trade
    price_risk = abs(entry_price - stop_loss_price)
    
    if price_risk == 0:
        return 0
    
    position_size = risk_amount / price_risk
    return position_size


if __name__ == '__main__':
    # 测试
    prices = [40000, 40500, 40200, 40800, 41000, 41500, 41200, 42000, 42500, 43000]
    regime = detect_market_regime(prices)
    print(f"Market Regime: {regime}")
    
    high = [41000, 41500, 41200, 41800, 42000, 42500, 42200, 43000, 43500, 44000]
    low = [39500, 40000, 39700, 40300, 40500, 41000, 40700, 41500, 42000, 42500]
    close = [40000, 40500, 40200, 40800, 41000, 41500, 41200, 42000, 42500, 43000]
    
    atr = calculate_atr(high, low, close)
    print(f"ATR: {atr}")
    
    if atr:
        sl = get_dynamic_stop_loss(43000, atr, regime)
        tp = get_dynamic_take_profit(43000, atr, regime)
        print(f"Entry: 43000, SL: {sl:.2f}, TP: {tp:.2f}")
