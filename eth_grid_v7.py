#!/usr/bin/env python3
"""
ETH 网格机器人 v7.1 优化版
- 成交驱动模式
- 动态网格间距
- 多线程架构
- ATR/波动率缓存
"""
import time
import json
import yaml
import os
import traceback
from datetime import datetime, date
import numpy as np
import pandas as pd
from binance.client import Client
from binance import ThreadedWebsocketManager
import threading
import queue

# ===================== 配置 =====================
CONFIG_FILE='config/exchange.yaml'
SYMBOL='ETHUSDT'
GRID_USDT=25
MAX_GRIDS=8
MAX_POSITION=0.2
MAX_ORDER_QTY=0.05  # 单次最大挂单量
LEVERAGE=10
STOP_LOSS=1970
TAKE_PROFIT=2080
ATR_PERIOD=14
LOG_FILE='grid_v7.log'
PNL_FILE='grid_v7_pnl.json'

ATR_MULT_MIN=0.8
ATR_MULT_MAX=1.5

# ===================== 缓存 =====================
price_cache=0
price_cache_time=0
protection="RANGE"
grid_center=None
last_grid_reset=0
twm=None

# ATR和波动率缓存
atr_cache=0
atr_cache_time=0
vol_cache=0
vol_cache_time=0

last_order_update=0

lock=threading.Lock()
msg_queue=queue.Queue()

# ===================== API =====================
with open(CONFIG_FILE) as f:
    cfg=yaml.safe_load(f)
client=Client(cfg['binance']['testnet']['api_key'], cfg['binance']['testnet']['secret_key'], testnet=True)

def get_precision():
    try:
        info=client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol']==SYMBOL:
                return s['quantityPrecision'], s['pricePrecision']
    except: return 3, 2
    return 3, 2

QTY_PREC, PRICE_PREC = get_precision()

# ===================== 飞书 =====================
def feishu_alert(msg):
    try:
        import requests
        webhook=cfg.get('feishu',{}).get('webhook','')
        if webhook:
            requests.post(webhook, json={"msg_type":"text","content":{"text":f"[ETH网格]{msg}"}}, timeout=5)
    except: pass

def log(msg, alert=False):
    t=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line=f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE,'a') as f:
        f.write(line+'\n')
    if alert:
        msg_queue.put(msg)

# ===================== PNL =====================
def load_pnl(): return json.load(open(PNL_FILE)) if os.path.exists(PNL_FILE) else {}
def save_pnl(p): json.dump(p,open(PNL_FILE,'w'))
def update_pnl(v):
    p=load_pnl()
    d=str(date.today())
    p[d]=p.get(d,0)+v
    save_pnl(p)

# ===================== WebSocket =====================
def handle_socket(msg):
    global price_cache, price_cache_time
    try:
        price_cache=float(msg['c'])
        price_cache_time=time.time()
    except: pass

def ws_thread():
    global twm, price_cache
    reconnect_count=0
    while True:
        try:
            if twm: twm.stop()
            twm=ThreadedWebsocketManager()
            twm.start()
            twm.start_symbol_ticker_socket(callback=handle_socket, symbol=SYMBOL)
            reconnect_count=0
            log("WS已连接")
            while True:
                time.sleep(30)
                if price_cache_time and (time.time()-price_cache_time)>60:
                    log("WS断线")
                    break
        except Exception as e:
            log(f"WS错误:{e}")
        reconnect_count+=1
        wait=min(30*reconnect_count, 300)
        log(f"WS重连 ({reconnect_count}), 等待{wait}秒")
        time.sleep(wait)

def get_price():
    global price_cache
    if price_cache and (time.time()-price_cache_time)<10:
        return price_cache
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])

# ===================== 市场数据 (缓存优化) =====================
def calc_atr():
    global atr_cache, atr_cache_time
    if atr_cache and (time.time()-atr_cache_time)<1800:  # 30分钟缓存
        return atr_cache
    
    kl=client.futures_klines(symbol=SYMBOL, interval='1h', limit=ATR_PERIOD+5)
    df=pd.DataFrame(kl)[[1,2,3,4]]
    df.columns=['open','high','low','close']
    df=df.astype(float)
    df['pc']=df['close'].shift(1)
    df=df.dropna()
    df['tr']=df.apply(lambda x:max(x['high']-x['low'],abs(x['high']-x['pc']),abs(x['low']-x['pc'])),axis=1)
    atr_cache = df['tr'].ewm(span=ATR_PERIOD).mean().iloc[-1]
    atr_cache_time = time.time()
    return atr_cache

def calc_volatility():
    global vol_cache, vol_cache_time
    if vol_cache and (time.time()-vol_cache_time)<1800:  # 30分钟缓存
        return vol_cache
    
    kl=client.futures_klines(symbol=SYMBOL, interval='1h', limit=20)
    closes=[float(k[4]) for k in kl]
    returns=np.diff(np.log(closes))
    vol_cache = np.std(returns)
    vol_cache_time = time.time()
    return vol_cache

def get_position():
    for p in client.futures_position_information(symbol=SYMBOL):
        amt=float(p['positionAmt'])
        if amt!=0:
            return {'side':'LONG' if amt>0 else 'SHORT','qty':abs(amt),'entry':float(p['entryPrice'])}
    return None

def get_pending_qty(side):
    total=0
    for o in client.futures_get_open_orders(symbol=SYMBOL):
        if o['side']==side:
            total+=float(o['origQty'])
    return total

# ===================== 网格 =====================
def get_atr_multiplier():
    vol=calc_volatility()
    if vol>0.03:
        return ATR_MULT_MAX
    elif vol<0.01:
        return ATR_MULT_MIN
    return 1.0

def generate_grid(center, atr):
    global grid_center
    if grid_center is None:
        # 用EMA20作为初始中心
        kl=client.futures_klines(symbol=SYMBOL, interval='1h', limit=20)
        closes=[float(k[4]) for k in kl]
        grid_center = np.mean(closes[-20:])  # SMA20近似EMA
    
    mult = get_atr_multiplier()
    spacing = atr * mult
    
    grids=[]
    for i in range(-MAX_GRIDS//2, MAX_GRIDS//2):
        g = round(grid_center + i*spacing, PRICE_PREC)
        if abs(g-center) < spacing*0.3:
            continue
        grids.append(g)
    return grids

def cancel_all():
    try:
        for o in client.futures_get_open_orders(symbol=SYMBOL):
            try:
                client.futures_cancel_order(symbol=SYMBOL, orderId=o['orderId'])
                time.sleep(0.05)
            except: pass
    except: pass

def place_order(side, price):
    with lock:
        pos = get_position()
        pending = get_pending_qty(side)
        current = pos['qty'] if pos else 0
        
        total = current + pending
        if total >= MAX_POSITION:
            log(f"达到最大持仓 {total}/{MAX_POSITION}")
            return False
        
        qty = round(GRID_USDT/price, QTY_PREC)
        # 单次挂单限制
        if qty > MAX_ORDER_QTY:
            qty = MAX_ORDER_QTY
        
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type='LIMIT',
                price=round(price, PRICE_PREC), quantity=qty,
                timeInForce='GTC'
            )
            log(f"挂单 {side} {price}")
            return True
        except Exception as e:
            log(f"挂单失败 {e}")
            return False

# ===================== 趋势 =====================
def trend_protection():
    global protection
    try:
        kl=client.futures_klines(symbol=SYMBOL, interval='5m', limit=50)
        closes=[float(k[4]) for k in kl]
        s=pd.Series(closes)
        ema5=s.ewm(span=5).mean().iloc[-1]
        ema10=s.ewm(span=10).mean().iloc[-1]
        ema20=s.ewm(span=20).mean().iloc[-1]
        
        if ema5>ema10>ema20:
            protection="UP"
        elif ema5<ema10<ema20:
            protection="DOWN"
        else:
            protection="RANGE"
    except:
        pass
    return protection

# ===================== 风控 =====================
def check_stop_loss(price, pos):
    if not pos:
        return False
    
    trigger=False
    if pos['side']=='LONG' and price<=STOP_LOSS:
        trigger=True
    elif pos['side']=='SHORT' and price>=STOP_LOSS:
        trigger=True
    
    if trigger:
        log(f"止损触发 {pos['side']}@{price}", alert=True)
        s='SELL' if pos['side']=='LONG' else 'BUY'
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=s, type='MARKET',
                quantity=round(pos['qty'], QTY_PREC), reduceOnly=True
            )
            fee=price*pos['qty']*0.0012
            pnl=(price-pos['entry'])*pos['qty'] if pos['side']=='LONG' else (pos['entry']-price)*pos['qty']
            pnl-=fee
            update_pnl(pnl)
            log(f"平仓 PnL:{pnl:.2f}", alert=True)
            cancel_all()
            return True
        except Exception as e:
            log(f"平仓失败 {e}")
    return False

# ===================== 成交驱动 =====================
def check_filled_orders():
    global last_order_update
    try:
        orders=client.futures_get_open_orders(symbol=SYMBOL)
        filled = MAX_GRIDS - len(orders)
        
        if filled > 0 and time.time()-last_order_update > 3:
            log(f"成交 {filled} 单, 补单")
            last_order_update = time.time()
            return True
    except:
        pass
    return False

# ===================== 主逻辑 =====================
def sync_grid(price, atr):
    global grid_center, last_grid_reset
    
    old_trend = protection
    trend = trend_protection()
    
    # 趋势变化重置
    if (old_trend!=trend and old_trend!="RANGE" and trend!="RANGE" 
        and time.time()-last_grid_reset>300):
        grid_center=None
        cancel_all()
        last_grid_reset=time.time()
        log(f"趋势变化 {old_trend}->{trend}, 重置", alert=True)
    
    # 中心漂移重置
    if grid_center and abs(price-grid_center) > atr*4:
        grid_center=None
        cancel_all()
        last_grid_reset=time.time()
        log(f"价格漂移重置")
    
    orders=client.futures_get_open_orders(symbol=SYMBOL)
    existing={round(float(o['price']), PRICE_PREC) for o in orders}
    grids=generate_grid(price, atr)
    count=len(orders)
    
    for g in grids:
        if count>=MAX_GRIDS:
            break
        if g in existing:
            continue
        
        side='BUY' if g<price else 'SELL'
        
        if trend=="UP" and side=="SELL":
            continue
        if trend=="DOWN" and side=="BUY":
            continue
        
        if place_order(side, g):
            count+=1

# ===================== 执行线程 =====================
def execution_thread():
    global last_order_update
    
    log("执行线程启动")
    while True:
        try:
            price=get_price()
            pos=get_position()
            atr=calc_atr()
            
            check_stop_loss(price, pos)
            
            # 成交驱动 + 定时30秒
            if check_filled_orders() or time.time()-last_order_update>30:
                sync_grid(price, atr)
            
            pnl_str=""
            if pos:
                fee=price*pos['qty']*0.0012
                pnl=(price-pos['entry'])*pos['qty'] if pos['side']=='LONG' else (pos['entry']-price)*pos['qty']
                pnl-=fee
                pnl_str=f", PnL:{pnl:.2f}"
            
            orders=client.futures_get_open_orders(symbol=SYMBOL)
            mult=get_atr_multiplier()
            log(f"价格:{price}, 挂单:{len(orders)}/{MAX_GRIDS}, ATRx{mult:.1f}, 趋势:{protection}{pnl_str}")
            
            time.sleep(5)
        except Exception as e:
            log(f"执行错误:{traceback.format_exc()}")
            time.sleep(30)

# ===================== 报警线程 =====================
def alert_thread():
    while True:
        try:
            msg=msg_queue.get(timeout=1)
            feishu_alert(msg)
        except:
            time.sleep(1)

# ===================== 主程序 =====================
def main():
    log("="*50)
    log("ETH Grid Bot v7.1 启动")
    log("="*50)
    
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except:
        pass
    
    threading.Thread(target=ws_thread, daemon=True).start()
    threading.Thread(target=execution_thread, daemon=True).start()
    threading.Thread(target=alert_thread, daemon=True).start()
    
    cancel_all()
    
    while True:
        time.sleep(60)

if __name__=="__main__":
    main()
