#!/usr/bin/env python3
"""
ETH 网格机器人 v6.4 最终版
"""
import time
import json
import yaml
import os
from datetime import datetime, date
import numpy as np
import pandas as pd
from binance.client import Client
from binance import ThreadedWebsocketManager
import threading

# 配置
CONFIG_FILE='config/exchange.yaml'
SYMBOL='ETHUSDT'
GRID_USDT=25
MAX_GRIDS=8
MAX_POSITION=0.2
LEVERAGE=10
STOP_LOSS=1970
TAKE_PROFIT=2080
ATR_PERIOD=14
ATR_MULTIPLIER=1.0
LOG_FILE='grid_v6.log'
PNL_FILE='grid_v6_pnl.json'

price_cache=None
price_cache_time=0
protection="RANGE"
grid_center=None
twm=None

# API
with open(CONFIG_FILE) as f:
    cfg=yaml.safe_load(f)
client=Client(cfg['binance']['testnet']['api_key'], cfg['binance']['testnet']['secret_key'], testnet=True)

# 精度
def get_precision():
    try:
        info=client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol']==SYMBOL:
                return s['quantityPrecision'], s['pricePrecision']
    except: return 3, 2
    return 3, 2

QTY_PREC, PRICE_PREC = get_precision()

# 日志 (带轮换)
def log(msg):
    t=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line=f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE,'a') as f:
        f.write(line+'\n')
    # 检查日志大小，超过10MB则备份
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE)>10*1024*1024:
        os.rename(LOG_FILE, LOG_FILE.replace('.log','_old.log'))

# PNL
def load_pnl(): return json.load(open(PNL_FILE)) if os.path.exists(PNL_FILE) else {}
def save_pnl(p): json.dump(p,open(PNL_FILE,'w'))
def update_pnl(v):
    p=load_pnl()
    d=str(date.today())
    p[d]=p.get(d,0)+v
    save_pnl(p)

# WebSocket
def handle_socket(msg):
    global price_cache, price_cache_time
    try: price_cache=float(msg['c']); price_cache_time=time.time()
    except: pass

def start_ws():
    global twm, price_cache
    while True:
        try:
            if twm: twm.stop()
            twm=ThreadedWebsocketManager(); twm.start()
            twm.start_symbol_ticker_socket(callback=handle_socket, symbol=SYMBOL)
            log("WS已连接")
            while True:
                time.sleep(30)
                if price_cache_time and (time.time()-price_cache_time)>60:
                    log("WS断线")
                    break
        except Exception as e: log(f"WS错误:{e}")
        time.sleep(5)

def get_price():
    global price_cache
    if price_cache and (time.time()-price_cache_time)<10: return price_cache
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])

# ATR
def calc_atr():
    kl=client.futures_klines(symbol=SYMBOL, interval='1h', limit=ATR_PERIOD+5)
    df=pd.DataFrame(kl)[[1,2,3,4]]; df.columns=['open','high','low','close']; df=df.astype(float)
    df['pc']=df['close'].shift(1); df=df.dropna()
    df['tr']=df.apply(lambda x:max(x['high']-x['low'],abs(x['high']-x['pc']),abs(x['low']-x['pc'])),axis=1)
    return df['tr'].ewm(span=ATR_PERIOD).mean().iloc[-1]

# 持仓
def get_position():
    for p in client.futures_position_information(symbol=SYMBOL):
        amt=float(p['positionAmt'])
        if amt!=0: return {'side':'LONG' if amt>0 else 'SHORT','qty':abs(amt),'entry':float(p['entryPrice'])}
    return None

# 获取待成交挂单数量
def get_pending_qty(side):
    total=0
    for o in client.futures_get_open_orders(symbol=SYMBOL):
        if o["side"]==side: total+=float(o["origQty"])
    return total

# 旧函数保留兼容
def get_pending_buy_qty_legacy():
    total=0
    for o in client.futures_get_open_orders(symbol=SYMBOL):
        if o['side']=='BUY':
            total+=float(o['origQty'])
    return total

# 生成网格
def generate_grid(center, atr):
    global grid_center
    if grid_center is None: grid_center = center
    spacing = atr * ATR_MULTIPLIER
    grids = []
    for i in range(-MAX_GRIDS//2, MAX_GRIDS//2):
        g = round(grid_center + i*spacing, PRICE_PREC)
        if abs(g-center) < spacing*0.3: continue
        grids.append(g)
    return grids

# 撤单
def cancel_all():
    for o in client.futures_get_open_orders(symbol=SYMBOL):
        try:
            client.futures_cancel_order(symbol=SYMBOL, orderId=o['orderId'])
            time.sleep(0.05)
        except: pass

# 下单 (修复: 计算持仓+挂单总量)
def place(side, price):
    pos = get_position()
    pending_qty = get_pending_qty(side)
    current_qty = pos['qty'] if pos else 0
    total_qty = current_qty + pending_qty
    
    if total_qty >= MAX_POSITION:
        log(f"达到最大持仓限制 {total_qty}/{MAX_POSITION}")
        return False
    
    qty = round(GRID_USDT/price, QTY_PREC)
    try:
        client.futures_create_order(symbol=SYMBOL, side=side, type='LIMIT', price=round(price,PRICE_PREC), quantity=qty, timeInForce='GTC')
        log(f"挂单 {side} {price}")
        return True
    except Exception as e:
        log(f"挂单失败 {e}")
        return False

# 趋势保护 (真EMA)
def trend_protection():
    global protection
    kl=client.futures_klines(symbol=SYMBOL, interval='5m', limit=50)
    closes=[float(k[4]) for k in kl]
    s=pd.Series(closes)
    ema5=s.ewm(span=5).mean().iloc[-1]
    ema10=s.ewm(span=10).mean().iloc[-1]
    ema20=s.ewm(span=20).mean().iloc[-1]
    if ema5>ema10>ema20: protection="UP"
    elif ema5<ema10<ema20: protection="DOWN"
    else: protection="RANGE"
    return protection

# 止损
def check_stop(price,pos):
    if not pos: return
    trigger=False
    if pos['side']=='LONG' and price<=STOP_LOSS: trigger=True
    if pos['side']=='SHORT' and price>=STOP_LOSS: trigger=True
    if trigger:
        log(f"止损 {pos['side']} @{price}")
        s='SELL' if pos['side']=='LONG' else 'BUY'
        try:
            client.futures_create_order(symbol=SYMBOL, side=s, type='MARKET', quantity=round(pos['qty'],QTY_PREC), reduceOnly=True)
            fee=price*pos["qty"]*0.0012
            pnl=(price-pos['entry'])*pos['qty'] if pos['side']=='LONG' else (pos['entry']-price)*pos['qty']
            pnl-=fee
            update_pnl(pnl)
            log(f"平仓 PnL:{pnl:.2f}")
            cancel_all()
        except Exception as e: log(f"平仓失败:{e}")

# 网格同步
def sync_grid(price,atr):
    global grid_center
    old_trend = protection
    trend = trend_protection()
    
    # 趋势变化时重置网格
    if old_trend!=trend and old_trend!="RANGE" and trend!="RANGE":
        grid_center=None
        cancel_all()
        log(f"趋势变化 {old_trend}->{trend}, 重置网格")
    
    # 修复: 中心漂移超过3倍ATR时重置
    if grid_center and abs(price-grid_center) > atr*3:
        grid_center=None
        cancel_all()
        log(f"价格漂移 {price-grid_center:.2f} > {atr*3:.2f}, 重置网格")
    
    orders=client.futures_get_open_orders(symbol=SYMBOL)
    existing={round(float(o['price']),PRICE_PREC) for o in orders}
    grids=generate_grid(price,atr)
    count=len(orders)
    
    for g in grids:
        if count>=MAX_GRIDS: break
        if g in existing: continue
        side='BUY' if g<price else 'SELL'
        if trend=="UP" and side=="SELL": continue
        if trend=="DOWN" and side=="BUY": continue
        if place(side,g): count+=1

# 主程序
def run():
    global protection
    log("ETH Grid Bot v6.4 启动")
    try: client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except: pass
    
    threading.Thread(target=start_ws, daemon=True).start()
    
    atr=calc_atr()
    last_atr=time.time()
    last_trend=time.time()
    last_orders=time.time()
    last_pos=time.time()
    cancel_all()
    
    while True:
        try:
            price=get_price()
            pos=None
            
            # 持仓每5秒
            if time.time()-last_pos>5:
                pos=get_position(); last_pos=time.time()
            
            # ATR每30分钟
            if time.time()-last_atr>1800:
                atr=calc_atr(); last_atr=time.time(); log(f"ATR:{atr:.2f}")
            
            # 趋势每60秒
            if time.time()-last_trend>60:
                trend_protection(); last_trend=time.time()
            
            check_stop(price,pos)
            
            # 挂单每10秒
            if time.time()-last_orders>10:
                sync_grid(price,atr); last_orders=time.time()
            
            pnl_str=""
            if pos:
                fee=price*pos["qty"]*0.0012
                pnl=(price-pos['entry'])*pos['qty'] if pos['side']=='LONG' else (pos['entry']-price)*pos['qty']
                pnl-=fee
                pnl_str=f", PnL:{pnl:.2f}"
            
            orders=client.futures_get_open_orders(symbol=SYMBOL)
            log(f"价格:{price}, 挂单:{len(orders)}/{MAX_GRIDS}, 趋势:{protection}{pnl_str}")
            time.sleep(5)
        except Exception as e:
            log(f"错误:{e}")
            time.sleep(10)

if __name__=="__main__":
    run()
