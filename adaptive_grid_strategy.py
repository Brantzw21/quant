"""
自适应ATR网格策略 v3
修复版 - 正确ATR计算
"""
import pandas as pd
from binance.client import Client
import yaml

with open('config/exchange.yaml') as f:
    config = yaml.safe_load(f)
client = Client(config['binance']['production']['api_key'], 
               config['binance']['production']['secret_key'], testnet=False)

# 参数 - 固定8%区间策略
SYMBOL = "ETHUSDT"
GRID_LEVELS = 10  # 网格数量
USDT_PER_GRID = 21
FIXED_PCT = 0.08  # 固定8%区间
STOP_LOSS_PCT = 0.02  # 2%止损
ATR_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 60


def get_ohlcv():
    """获取K线数据"""
    klines = client.get_klines(symbol=SYMBOL, interval='5m', limit=200)
    data = []
    for k in klines:
        data.append({
            'o': float(k[1]),
            'h': float(k[2]),
            'l': float(k[3]),
            'c': float(k[4])
        })
    df = pd.DataFrame(data)
    return df


def calculate_indicators():
    """计算指标 - 正确的ATR计算"""
    df = get_ohlcv()
    
    # 正确的TR计算
    df['prev_close'] = df['c'].shift(1)
    df['tr'] = df[['h', 'prev_close']].max(axis=1) - df[['l', 'prev_close']].min(axis=1)
    atr = df['tr'].rolling(ATR_PERIOD).mean().iloc[-1]
    
    # EMA趋势
    df['ema_fast'] = df['c'].ewm(span=EMA_FAST).mean()
    df['ema_slow'] = df['c'].ewm(span=EMA_SLOW).mean()
    
    price = df['c'].iloc[-1]
    trend = 'up' if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] else 'down'
    
    # 波动率
    vol_ratio = atr / price * 100
    
    return price, atr, trend, vol_ratio


def build_grid():
    """构建网格 - 固定8%区间"""
    price, atr, trend, vol_ratio = calculate_indicators()
    
    # 固定8%区间
    grid_size = price * FIXED_PCT / GRID_LEVELS
    lower = price * (1 - FIXED_PCT)
    upper = price * (1 + FIXED_PCT)
    
    grids = []
    p = lower
    while p <= upper:
        grids.append(round(p, 2))
        p += grid_size
    
    return {
        'price': price,
        'atr': atr,
        'trend': trend,
        'vol_ratio': vol_ratio,
        'grid_size': grid_size,
        'grids': grids,
        'lower': lower,
        'upper': upper,
        'stop_loss': lower * (1 - STOP_LOSS_PCT)
    }


def get_signal():
    """获取交易信号"""
    info = build_grid()
    
    return {
        'price': info['price'],
        'atr': info['atr'],
        'trend': info['trend'],
        'vol_ratio': info['vol_ratio'],
        'grid_size': info['grid_size'],
        'grids': info['grids'],
        'lower_bound': info['lower'],
        'upper_bound': info['upper'],
        'stop_loss': info['stop_loss'],
        'strategy': 'fixed_8pct',
        'pause_strategy': False
    }


if __name__ == '__main__':
    s = get_signal()
    print(f"价格: ${s['price']:.2f}")
    print(f"ATR: {s['atr']:.2f}")
    print(f"波动率: {s['vol_ratio']:.2f}%")
    print(f"网格: {s['grid_size']:.2f}")
    print(f"趋势: {s['trend']}")
    print(f"区间: {s['lower_bound']:.0f} - {s['upper_bound']:.0f}")
    print(f"止损: {s['stop_loss']:.0f}")
    print(f"暂停: {s['pause_strategy']}")
