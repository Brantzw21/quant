#!/usr/bin/env python3
"""
ETH 窄区间网格机器人 v3.1 - 优化版
区间: $1990-$2060, 16格, 止损$1970
模拟盘运行

优化内容(v3.1):
1. 网格方向: 低于当前价BUY(低买), 高于当前价SELL(高卖)
2. 止损逻辑: 用side判断而非amount
3. 资金控制: 每格固定20U,最多同时8格
4. 挂单数量控制: 保证网格完整 (< MAX_GRIDS 补单)
5. 日志记录: 成交记录 + PnL 记录
"""
import time
import yaml
import json
from datetime import datetime
from binance.client import Client

# 配置
CONFIG_FILE = 'config/exchange.yaml'
SYMBOL = 'ETHUSDT'

# 窄区间网格参数
GRID_LOWER = 1990   # 区间下限
GRID_UPPER = 2060   # 区间上限
GRID_COUNT = 16      # 网格数量
STOP_LOSS = 1970    # 止损
TAKE_PROFIT = 2080  # 止盈(可选)
GRID_SIZE = (GRID_UPPER - GRID_LOWER) / GRID_COUNT

# 资金控制
GRID_USDT = 20      # 每格20U
MAX_GRIDS = 8       # 最多同时8格
LEVERAGE = 10

# 日志文件
LOG_FILE = 'grid_bot_v3_log.json'

# 加载配置
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

# 测试网
client = Client(
    config['binance']['testnet']['api_key'],
    config['binance']['testnet']['secret_key'],
    testnet=True
)

STATE_FILE = 'grid_bot_v3_state.json'


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {'orders': [], 'position': 0}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def load_log():
    """加载日志"""
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except:
        return {'trades': [], 'daily_pnl': []}


def save_log(log_data):
    """保存日志"""
    with open(LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)


def log_trade(trade_type, price, qty, side, pnl=0):
    """记录成交"""
    log = load_log()
    log['trades'].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': trade_type,
        'price': price,
        'qty': qty,
        'side': side,
        'pnl': pnl
    })
    # 只保留最近100条
    log['trades'] = log['trades'][-100:]
    save_log(log)


def log_pnl():
    """记录每日盈亏"""
    log = load_log()
    pos = get_position()
    price = get_price()
    
    if pos:
        pnl = (price - pos['entry']) * pos['amount'] if pos['side'] == 'LONG' else (pos['entry'] - price) * pos['amount']
    else:
        pnl = 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 更新今日盈亏
    found = False
    for d in log.get('daily_pnl', []):
        if d['date'] == today:
            d['pnl'] = pnl
            found = True
    
    if not found:
        log['daily_pnl'] = log.get('daily_pnl', []) + [{'date': today, 'pnl': pnl}]
    
    # 只保留最近30天
    log['daily_pnl'] = log['daily_pnl'][-30:]
    save_log(log)


def get_price():
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])


def get_position():
    """获取当前持仓"""
    for p in client.futures_position_information(symbol=SYMBOL):
        amt = float(p.get('positionAmt', 0))
        if amt != 0:
            return {
                'amount': abs(amt),
                'entry': float(p.get('entryPrice', 0)),
                'side': 'LONG' if amt > 0 else 'SHORT',
            }
    return None


def place_single_order(grid_price, current_price):
    """挂单个网格单"""
    qty = GRID_USDT / grid_price
    qty = round(max(qty, 0.001), 3)
    
    # 低于当前价BUY(低买), 高于当前价SELL(高卖)
    if grid_price < current_price:
        side = 'BUY'
    else:
        side = 'SELL'
    
    try:
        order = client.futures_create_order(
            symbol=SYMBOL, side=side, type='LIMIT',
            quantity=qty, price=grid_price,
            timeInForce='GTC', positionSide='BOTH'
        )
        print(f"挂单: {side} ${grid_price} x {qty}")
        return {'price': grid_price, 'side': side, 'id': order['orderId']}
    except Exception as e:
        print(f"挂单失败: {e}")
        return None


def sync_and_place_grid():
    """同步订单状态并挂单 - 优化版"""
    current_price = get_price()
    
    # 查询当前挂单
    open_orders = client.futures_get_open_orders(symbol=SYMBOL)
    existing_prices = {round(float(o['price']), 2): o for o in open_orders}
    
    print(f"当前价格: ${current_price}, 现有挂单: {len(open_orders)}/{MAX_GRIDS}")
    
    # 计算目标价格范围
    target_prices = []
    for i in range(GRID_COUNT + 1):
        grid_price = round(GRID_LOWER + i * GRID_SIZE, 2)
        # 挂当前价格附近的单
        if abs(grid_price - current_price) <= GRID_SIZE * (MAX_GRIDS // 2 + 1):
            target_prices.append(grid_price)
    
    # 补挂缺失的订单 (优化: 保持MAX_GRIDS个)
    placed = 0
    for grid_price in target_prices:
        if len(open_orders) + placed >= MAX_GRIDS:
            break
        if grid_price not in existing_prices:
            result = place_single_order(grid_price, current_price)
            if result:
                placed += 1
    
    print(f"补挂单完成: {placed} 个, 现有: {len(open_orders) + placed}/{MAX_GRIDS}")
    return placed


def check_stop_loss():
    """检查止损"""
    price = get_price()
    pos = get_position()
    
    if not pos:
        return False
    
    # 止损
    if price < STOP_LOSS:
        print(f"⚠️ 触发止损: ${price} < ${STOP_LOSS}")
        side = 'SELL' if pos['side'] == 'LONG' else 'BUY'
        pnl = (price - pos['entry']) * pos['amount'] if pos['side'] == 'LONG' else (pos['entry'] - price) * pos['amount']
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type='MARKET',
                quantity=round(pos['amount'], 3)
            )
            print("✅ 止损平仓")
            log_trade('STOP_LOSS', price, pos['amount'], pos['side'], pnl)
            return True
        except Exception as e:
            print(f"止损失败: {e}")
    
    # 止盈
    if price > TAKE_PROFIT:
        print(f"💰 触发止盈: ${price} > ${TAKE_PROFIT}")
        side = 'SELL' if pos['side'] == 'LONG' else 'BUY'
        pnl = (price - pos['entry']) * pos['amount'] if pos['side'] == 'LONG' else (pos['entry'] - price) * pos['amount']
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type='MARKET',
                quantity=round(pos['amount'], 3)
            )
            print("✅ 止盈平仓")
            log_trade('TAKE_PROFIT', price, pos['amount'], pos['side'], pnl)
            return True
        except Exception as e:
            print(f"止盈失败: {e}")
    
    return False


def check_filled_orders():
    """检查成交并记录"""
    try:
        orders = client.futures_get_all_orders(symbol=SYMBOL, limit=5)
        for o in orders[-3:]:
            if o['status'] == 'FILLED' and o.get('updateTime', 0) > (time.time() - 300) * 1000:
                # 检查是否已记录
                log = load_log()
                if not any(t.get('id') == o['orderId'] for t in log.get('trades', [])):
                    log_trade('FILLED', float(o['price']), float(o['origQty']), o['side'], 0)
                    print(f"📝 记录成交: {o['side']} ${o['price']}")
    except:
        pass


def run():
    print("="*50)
    print("ETH 窄区间网格机器人 v3.1 (优化版)")
    print(f"区间: ${GRID_LOWER} - ${GRID_UPPER}")
    print(f"网格: {GRID_COUNT} 格, 间距 ${GRID_SIZE:.2f}")
    print(f"止损: ${STOP_LOSS}, 止盈: ${TAKE_PROFIT}")
    print(f"每格: ${GRID_USDT}, 最多: {MAX_GRIDS}格")
    print("="*50)
    
    state = load_state()
    
    # 设置杠杆
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except:
        pass
    
    # 初始挂单
    sync_and_place_grid()
    
    last_check = time.time()
    
    while True:
        try:
            price = get_price()
            pos = get_position()
            
            pnl_str = ""
            if pos:
                pnl = (price - pos['entry']) * pos['amount'] if pos['side'] == 'LONG' else (pos['entry'] - price) * pos['amount']
                pnl_str = f", 持仓: {pos['amount']:.3f} ETH, 盈亏: ${pnl:.2f}"
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 价格: ${price}{pnl_str}")
            
            # 检查止损止盈
            if check_stop_loss():
                time.sleep(2)
                sync_and_place_grid()
            
            # 检查成交
            check_filled_orders()
            
            # 优化: 挂单不足MAX_GRIDS时补单
            open_orders = client.futures_get_open_orders(symbol=SYMBOL)
            if len(open_orders) < MAX_GRIDS:
                print(f"挂单不足({len(open_orders)}/{MAX_GRIDS}), 补挂...")
                sync_and_place_grid()
            
            # 记录每日盈亏
            log_pnl()
            
            # 每3分钟检查一次
            time.sleep(180)
            
        except Exception as e:
            print(f"错误: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run()
