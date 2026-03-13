#!/usr/bin/env python3
"""
ETH Grid Bot v7.3
Stable Professional Grid Trading Bot
"""

import time
import yaml
import threading
import traceback
from datetime import datetime
import numpy as np
import pandas as pd
from binance.client import Client
from binance import ThreadedWebsocketManager

# ===================== CONFIG =====================
CONFIG_FILE="config/exchange.yaml"
SYMBOL="ETHUSDT"
GRID_USDT=25
MAX_GRIDS=8
MAX_POSITION=0.2
MAX_ORDER_QTY=0.05
ATR_PERIOD=14
ATR_MULT_MIN=0.8
ATR_MULT_MAX=1.0
MAX_GRID_DISTANCE=0.04
LEVERAGE=10
STOP_LOSS_BUFFER=0.035
GRID_RESET_BUFFER=0.03
LOG_FILE="grid_v7.log"

# ===================== STATE =====================
price_cache=0
price_cache_time=0
pos_cache=None
pos_cache_time=0
orders_cache=None
orders_cache_time=0
atr_cache=None
atr_cache_time=0
cooldown_until=0
grid_center=None
lock=threading.Lock()

# ===================== API =====================
with open(CONFIG_FILE) as f:
    cfg=yaml.safe_load(f)

WEBHOOK_URL = cfg.get('webhook', {}).get('url', '')
WEBHOOK_ENABLED = cfg.get('webhook', {}).get('enabled', False)

import requests
def send_webhook(msg):
    if not WEBHOOK_ENABLED or not WEBHOOK_URL:
        return
    try:
        requests.post(WEBHOOK_URL, json={'msg_type':'text','content':{'text':msg}}, timeout=5)
    except:
        pass

client=Client(
    cfg['binance']['production']['api_key'],
    cfg['binance']['production']['secret_key']
)

# ===================== UTIL =====================
def log(msg, alert=False):
    t=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line=f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE,"a") as f:
        f.write(line+"\n")
    if alert:
        send_webhook(line)

# ===================== WS PRICE =====================
def handle_price(msg):
    global price_cache,price_cache_time
    try:
        price_cache=float(msg['c'])
        price_cache_time=time.time()
    except:
        pass

# ===================== USER STREAM =====================
def handle_user(msg):
    try:
        if msg['e']=="ORDER_TRADE_UPDATE":
            o=msg['o']
            if o['X']=="FILLED":
                log(f"成交 {o['S']} {o['p']}")
    except:
        pass

# ===================== WS THREAD =====================
def ws_thread():
    twm=ThreadedWebsocketManager()
    twm.start()
    twm.start_symbol_ticker_socket(callback=handle_price, symbol=SYMBOL)
    log("WebSocket started")
    while True:
        time.sleep(1800)

# ===================== PRICE =====================
def get_price():
    if price_cache and time.time()-price_cache_time<10:
        return price_cache
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])

# ===================== POSITION =====================
def get_position():
    global pos_cache,pos_cache_time
    if pos_cache and time.time()-pos_cache_time<15:
        return pos_cache
    try:
        for p in client.futures_position_information(symbol=SYMBOL):
            amt=float(p['positionAmt'])
            if amt!=0:
                pos_cache={"qty":abs(amt),"signed":amt,"entry":float(p['entryPrice'])}
                pos_cache_time=time.time()
                return pos_cache
    except:
        pass
    pos_cache=None
    pos_cache_time=time.time()
    return None

# ===================== ORDERS =====================
def get_orders():
    global orders_cache,orders_cache_time
    if orders_cache is not None and time.time()-orders_cache_time<5:
        return orders_cache
    try:
        orders_cache=client.futures_get_open_orders(symbol=SYMBOL)
        orders_cache_time=time.time()
    except:
        pass
    return orders_cache or []

# ===================== ATR =====================
def calc_atr():
    global atr_cache,atr_cache_time
    if atr_cache and time.time()-atr_cache_time<1800:
        return atr_cache
    kl=client.futures_klines(symbol=SYMBOL, interval="1h", limit=ATR_PERIOD+5)
    df=pd.DataFrame(kl)[[1,2,3,4]]
    df.columns=["open","high","low","close"]
    df=df.astype(float)
    df['pc']=df['close'].shift(1)
    df=df.dropna()
    df['tr']=df.apply(lambda x:max(x['high']-x['low'],abs(x['high']-x['pc']),abs(x['low']-x['pc'])),axis=1)
    atr=df['tr'].ewm(span=ATR_PERIOD).mean().iloc[-1]
    atr_cache=atr
    atr_cache_time=time.time()
    return atr

# ===================== GRID =====================
def generate_grid(price,atr):
    global grid_center
    if grid_center is None:
        grid_center=price
    vol=atr/price
    mult=ATR_MULT_MAX if vol>0.015 else ATR_MULT_MIN
    spacing=max(atr*mult, price*0.01)
    grids=[]
    for i in range(-MAX_GRIDS//2,MAX_GRIDS//2 + 1):
        g=round(grid_center+i*spacing,2)
        if abs(g-price)/price > MAX_GRID_DISTANCE:
            continue
        grids.append(g)
    return grids

# ===================== INVENTORY =====================
def inventory_ratio():
    pos=get_position()
    if not pos:
        return 0
    return pos['signed']/MAX_POSITION

# ===================== ORDER =====================
def place_order(side,price):
    with lock:
        qty=GRID_USDT/price
        if qty>MAX_ORDER_QTY:
            qty=MAX_ORDER_QTY
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type="LIMIT",
                price=round(price,2), quantity=round(qty,3), timeInForce="GTC"
            )
            log(f"挂单 {side} {price}")
        except Exception as e:
            log(f"下单失败 {e}")

# ===================== GRID ENGINE =====================
def sync_grid():
    global grid_center
    price=get_price()
    atr=calc_atr()
    reset_threshold=max(atr*4, price*GRID_RESET_BUFFER)
    if grid_center and abs(price-grid_center)>reset_threshold:
        grid_center=price
        log(f"Grid center reset {price}")
    grids=generate_grid(price,atr)
    orders=get_orders()
    existing={round(float(o['price']),2) for o in orders}
    inv=inventory_ratio()
    count=len(orders)
    for g in grids:
        if count>=MAX_GRIDS:
            break
        if g in existing:
            continue
        side="BUY" if g<price else "SELL"
        if side=="BUY" and inv>0.7:
            continue
        if side=="SELL" and inv<-0.7:
            continue
        place_order(side,g)
        count+=1

# ===================== STOP LOSS =====================
def check_stop():
    global cooldown_until
    pos=get_position()
    if not pos:
        return
    price=get_price()
    if pos['signed']>0:
        stop_price=pos['entry']*(1-STOP_LOSS_BUFFER)
        if price<=stop_price:
            side="SELL"
        else:
            return
    elif pos['signed']<0:
        stop_price=pos['entry']*(1+STOP_LOSS_BUFFER)
        if price>=stop_price:
            side="BUY"
        else:
            return
    else:
        return
    try:
        client.futures_create_order(symbol=SYMBOL, side=side, type="MARKET", quantity=pos['qty'], reduceOnly=True)
        log(f"止损触发 @ {price:.2f}", alert=True)
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
        cooldown_until=time.time()+600
    except Exception as e:
        log(f"止损失败 {e}")

# ===================== EXECUTION =====================
def execution_thread():
    log("Execution started")
    while True:
        try:
            if time.time()<cooldown_until:
                log("止损冷却中")
                time.sleep(10)
                continue
            check_stop()
            sync_grid()
            price=get_price()
            orders=len(get_orders())
            log(f"价格 {price} 挂单 {orders}/{MAX_GRIDS}")
            time.sleep(5)
        except:
            log(traceback.format_exc())
            time.sleep(30)

# ===================== MAIN =====================
def main():
    log("Grid Bot v7.3 Start")
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except:
        pass
    threading.Thread(target=ws_thread,daemon=True).start()
    threading.Thread(target=execution_thread,daemon=True).start()
    while True:
        time.sleep(60)

if __name__=="__main__":
    main()
