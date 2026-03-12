#!/usr/bin/env python3
"""
ETH 网格机器人 v4 - 简化版
使用轮询替代 WebSocket
特性：
1. ATR 动态刷新
2. 实时止损检查(每10秒)
3. 自动补单
4. 日志记录
"""
import time
import json
import yaml
import os
from datetime import datetime, date
from binance.client import Client
import pandas as pd

# ===================== 配置 =====================
CONFIG_FILE = 'config/exchange.yaml'
SYMBOL = 'ETHUSDT'
GRID_USDT = 20
MAX_GRIDS = 8
LEVERAGE = 10
STOP_LOSS = 1970
TAKE_PROFIT = 2080
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.0

STATE_FILE = 'grid_bot_v4_state.json'
LOG_FILE = 'grid_bot_v4.log'
DAILY_PNL_FILE = 'grid_bot_v4_daily_pnl.json'

# ===================== 加载配置 =====================
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

TESTNET = True
client = Client(
    config['binance']['testnet']['api_key'],
    config['binance']['testnet']['secret_key'],
    testnet=TESTNET
)

# ===================== 工具函数 =====================
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {msg}\n")


def load_daily_pnl():
    if os.path.exists(DAILY_PNL_FILE):
        with open(DAILY_PNL_FILE) as f:
            return json.load(f)
    return {str(date.today()): 0}


def save_daily_pnl(pnl_dict):
    with open(DAILY_PNL_FILE, 'w') as f:
        json.dump(pnl_dict, f)


def get_price():
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])


def get_position():
    for p in client.futures_position_information(symbol=SYMBOL):
        amt = float(p.get('positionAmt', 0))
        if amt != 0:
            return {
                'amount': abs(amt),
                'entry': float(p.get('entryPrice', 0)),
                'side': 'LONG' if amt > 0 else 'SHORT',
            }
    return None


def calc_atr():
    klines = client.futures_klines(symbol=SYMBOL, interval='1h', limit=ATR_PERIOD+1)
    df = pd.DataFrame(klines, columns=['open','high','low','close','ct','q','n','tbv','tbq','i','i2','ignore'])
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['prev_close'] = df['close'].shift(1)
    df = df.dropna()
    df['tr'] = df[['high','low','prev_close']].apply(
        lambda x: max(x['high']-x['low'], abs(x['high']-x['prev_close']), abs(x['low']-x['prev_close'])), axis=1)
    return df['tr'].rolling(ATR_PERIOD).mean().iloc[-1]


def place_order(side, price, qty):
    try:
        order = client.futures_create_order(
            symbol=SYMBOL, side=side, type='LIMIT',
            quantity=qty, price=round(price, 2),
            timeInForce='GTC', positionSide='BOTH'
        )
        return True
    except Exception as e:
        return False


def update_daily_pnl(pnl):
    pnl_dict = load_daily_pnl()
    today = str(date.today())
    if today not in pnl_dict:
        pnl_dict[today] = 0
    pnl_dict[today] += pnl
    save_daily_pnl(pnl_dict)


def generate_grid(current_price, atr):
    grid_spacing = atr * ATR_MULTIPLIER
    prices = []
    for i in range(-MAX_GRIDS//2, MAX_GRIDS//2 + 1):
        prices.append(round(current_price + i*grid_spacing, 2))
    return prices


def check_stop_loss(price, pos):
    """实时止损检查"""
    if not pos:
        return False
    
    triggered = False
    
    # 止损
    if pos['side']=='LONG' and price < STOP_LOSS:
        triggered = True
        log(f"⚠️ 止损触发: ${price} < ${STOP_LOSS}")
    elif pos['side']=='SHORT' and price > TAKE_PROFIT:
        triggered = True
        log(f"⚠️ 止盈触发: ${price} > ${TAKE_PROFIT}")
    
    if triggered:
        side = 'SELL' if pos['side']=='LONG' else 'BUY'
        try:
            client.futures_create_order(symbol=SYMBOL, side=side, type='MARKET', quantity=round(pos['amount'], 3))
            pnl = round((price - pos['entry']) * pos['amount'] if pos['side']=='LONG' else (pos['entry'] - price) * pos['amount'], 2)
            update_daily_pnl(pnl)
            log(f"✅ 平仓完成, PnL: ${pnl}")
            return True
        except Exception as e:
            log(f"平仓失败: {e}")
    
    return False


def sync_grid(price, atr):
    """同步网格"""
    open_orders = client.futures_get_open_orders(symbol=SYMBOL)
    
    if len(open_orders) >= MAX_GRIDS:
        return
    
    grid_prices = generate_grid(price, atr)
    existing = {round(float(o['price']), 2) for o in open_orders}
    
    for gp in grid_prices:
        if len(open_orders) >= MAX_GRIDS:
            break
        if gp not in existing:
            side = 'BUY' if gp < price else 'SELL'
            qty = round(GRID_USDT/gp, 3)
            if place_order(side, gp, qty):
                log(f"挂单 {side} ${gp} x {qty}")


def run():
    log("="*50)
    log("ETH 网格机器人 v4 启动")
    log("="*50)
    
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except:
        pass
    
    atr = calc_atr()
    last_atr_update = time.time()
    log(f"初始ATR: {atr:.2f}")
    
    while True:
        try:
            price = get_price()
            pos = get_position()
            
            # 每60秒刷新ATR
            if time.time() - last_atr_update > 60:
                atr = calc_atr()
                last_atr_update = time.time()
                log(f"ATR刷新: {atr:.2f}, 区间: ${price - atr*4:.0f} - ${price + atr*4:.0f}")
            
            # 实时止损检查
            if pos and check_stop_loss(price, pos):
                time.sleep(2)
            
            # 同步网格
            sync_grid(price, atr)
            
            # 状态输出
            pnl_str = ""
            if pos:
                pnl = (price - pos['entry']) * pos['amount'] if pos['side']=='LONG' else (pos['entry'] - price) * pos['amount']
                pnl_str = f", 持仓:{pos['amount']:.3f}ETH, PnL:${pnl:.2f}"
            
            open_orders = client.futures_get_open_orders(symbol=SYMBOL)
            log(f"价格:${price}, 挂单:{len(open_orders)}/{MAX_GRIDS}{pnl_str}")
            
            time.sleep(10)  # 每10秒检查一次
            
        except Exception as e:
            log(f"错误: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run()
