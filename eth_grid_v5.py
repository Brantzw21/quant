#!/usr/bin/env python3
"""
ETH 网格机器人 v5.1 - 专业量化版
特性：
1. ATR 动态刷新
2. 实时止损/止盈检查(每10秒)
3. 自动补单
4. 日志记录
5. 单边行情保护模式
"""
import time
import json
import yaml
import os
from datetime import datetime, date
from binance.client import Client
import pandas as pd
import numpy as np

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

STATE_FILE = 'grid_bot_v5_state.json'
LOG_FILE = 'grid_bot_v5.log'
DAILY_PNL_FILE = 'grid_bot_v5_daily_pnl.json'

# 单边保护参数
EMA_SHORT = 5
EMA_MID = 10
EMA_LONG = 20
PROTECTION_TRIGGER = 0.01  # 连续涨跌幅 >1%触发保护
PROTECTION_ACTIVE = False

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
        client.futures_create_order(
            symbol=SYMBOL, side=side, type='LIMIT',
            quantity=round(qty,3), price=round(price, 2),
            timeInForce='GTC', positionSide='BOTH'
        )
        return True
    except Exception as e:
        log(f"挂单失败: {e}")
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

# ===================== 单边行情保护 =====================
def get_recent_closes(limit=EMA_LONG+5):
    klines = client.futures_klines(symbol=SYMBOL, interval='5m', limit=limit)
    closes = [float(k[4]) for k in klines]
    return closes

def check_market_protection():
    global PROTECTION_ACTIVE
    closes = get_recent_closes()
    closes_arr = np.array(closes)

    ema_short = closes_arr[-EMA_SHORT:].mean()
    ema_mid = closes_arr[-EMA_MID:].mean()
    ema_long = closes_arr[-EMA_LONG:].mean()

    # 单边上涨
    if ema_short > ema_mid > ema_long and (closes[-1]-closes[0])/closes[0] > PROTECTION_TRIGGER:
        if not PROTECTION_ACTIVE:
            log(f"⚠️ 单边上涨保护模式启动, 停止新买单")
        PROTECTION_ACTIVE = True
    # 单边下跌
    elif ema_short < ema_mid < ema_long and (closes[0]-closes[-1])/closes[0] > PROTECTION_TRIGGER:
        if not PROTECTION_ACTIVE:
            log(f"⚠️ 单边下跌保护模式启动, 停止新卖单")
        PROTECTION_ACTIVE = True
    else:
        if PROTECTION_ACTIVE:
            log(f"✅ 市场回归震荡, 保护模式关闭")
        PROTECTION_ACTIVE = False
    
    return PROTECTION_ACTIVE

def sync_grid_with_protection(price, atr):
    global PROTECTION_ACTIVE
    PROTECTION_ACTIVE = check_market_protection()
    
    open_orders = client.futures_get_open_orders(symbol=SYMBOL)
    if len(open_orders) >= MAX_GRIDS:
        return

    grid_prices = generate_grid(price, atr)
    existing = {round(float(o['price']),2) for o in open_orders}
    
    closes = get_recent_closes()

    for gp in grid_prices:
        if len(open_orders) >= MAX_GRIDS:
            break
        if gp in existing:
            continue
        
        side = 'BUY' if gp < price else 'SELL'
        
        # 保护模式过滤
        if PROTECTION_ACTIVE:
            if side=='BUY' and closes[-1] > closes[0]:
                continue
            if side=='SELL' and closes[-1] < closes[0]:
                continue
        
        qty = round(GRID_USDT/gp, 3)
        if place_order(side, gp, qty):
            log(f"挂单 {side} ${gp} x {qty} (保护:{PROTECTION_ACTIVE})")

# ===================== 止损/止盈 =====================
def check_stop_loss(price, pos):
    if not pos:
        return False

    triggered = False

    # LONG止损 / SHORT止盈
    if pos['side']=='LONG' and price < STOP_LOSS:
        triggered = True
        log(f"⚠️ 止损触发: ${price} < ${STOP_LOSS}")
    elif pos['side']=='SHORT' and price > TAKE_PROFIT:
        triggered = True
        log(f"⚠️ 止盈触发: ${price} > ${TAKE_PROFIT}")

    if triggered:
        side = 'SELL' if pos['side']=='LONG' else 'BUY'
        try:
            client.futures_create_order(symbol=SYMBOL, side=side, type='MARKET', quantity=round(pos['amount'],3))
            pnl = round((price - pos['entry']) * pos['amount'] if pos['side']=='LONG' else (pos['entry'] - price) * pos['amount'], 2)
            update_daily_pnl(pnl)
            log(f"✅ 平仓完成, PnL: ${pnl}")
            return True
        except Exception as e:
            log(f"平仓失败: {e}")
    return False

# ===================== 主循环 =====================
def run():
    log("="*50)
    log("ETH 网格机器人 v5.1 启动")
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
                log(f"ATR刷新: {atr:.2f}")

            # 实时止损/止盈
            if pos and check_stop_loss(price, pos):
                time.sleep(2)

            # 同步网格(带保护)
            sync_grid_with_protection(price, atr)

            # 状态输出
            pnl_str = ""
            if pos:
                pnl = (price - pos['entry']) * pos['amount'] if pos['side']=='LONG' else (pos['entry'] - price) * pos['amount']
                pnl_str = f", PnL:${pnl:.2f}"

            open_orders = client.futures_get_open_orders(symbol=SYMBOL)
            log(f"价格:${price}, 挂单:{len(open_orders)}/{MAX_GRIDS}, 保护:{PROTECTION_ACTIVE}{pnl_str}")

            time.sleep(10)

        except Exception as e:
            log(f"错误: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run()
