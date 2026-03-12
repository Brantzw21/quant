#!/usr/bin/env python3
"""
ETH 窄区间网格机器人 v2
区间: $1990-$2060, 16格, 止损$1970
模拟盘运行
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
GRID_COUNT = 16     # 网格数量
STOP_LOSS = 1970    # 止损
TAKE_PROFIT = 2080  # 止盈(可选)
GRID_SIZE = (GRID_UPPER - GRID_LOWER) / GRID_COUNT

TOTAL_USDT = 200    # 总资金 (测试网最小20U/单)
LEVERAGE = 10

# 加载配置
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

# 测试网
client = Client(
    config['binance']['testnet']['api_key'],
    config['binance']['testnet']['secret_key'],
    testnet=True
)

STATE_FILE = 'grid_bot_v2_state.json'


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {'orders': {}, 'last_price': 0}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


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
                'pnl': float(p.get('unrealizedProfit', 0))
            }
    return None


def cancel_all():
    """取消所有挂单"""
    orders = client.futures_get_open_orders(symbol=SYMBOL)
    for o in orders:
        client.futures_cancel_order(symbol=SYMBOL, orderId=o['orderId'])
    print(f"取消 {len(orders)} 个挂单")


def place_grid():
    """挂网格单 - 每次先取消所有挂单"""
    current_price = get_price()
    placed = 0
    
    # 先取消所有挂单（防止重复挂单）
    cancel_all()
    
    # 每格金额 (最少20U)
    min_usdt = 20
    usdt_per_grid = max(TOTAL_USDT / GRID_COUNT, min_usdt)
    
    # 需要挂单的价格列表
    target_prices = []
    for i in range(GRID_COUNT + 1):
        grid_price = round(GRID_LOWER + i * GRID_SIZE, 2)
        # 只挂当前价格附近的单 (±2格范围内)
        if abs(grid_price - current_price) <= GRID_SIZE * 2:
            target_prices.append(grid_price)
    
    print(f"目标挂单价格: {target_prices}")
    
    for grid_price in target_prices:
        qty = usdt_per_grid / grid_price
        qty = round(max(qty, 0.001), 3)
        
        # 低于当前价 -> 卖单(做空)
        if grid_price < current_price:
            try:
                order = client.futures_create_order(
                    symbol=SYMBOL, side='SELL', type='LIMIT',
                    quantity=qty, price=grid_price,
                    timeInForce='GTC', positionSide='BOTH'
                )
                print(f"挂空单 ${grid_price} x {qty} -> ID:{order['orderId']}")
                placed += 1
            except Exception as e:
                print(f"挂空单失败: {e}")
        
        # 高于当前价 -> 买单(做多)
        else:
            try:
                order = client.futures_create_order(
                    symbol=SYMBOL, side='BUY', type='LIMIT',
                    quantity=qty, price=grid_price,
                    timeInForce='GTC', positionSide='BOTH'
                )
                print(f"挂多单 ${grid_price} x {qty} -> ID:{order['orderId']}")
                placed += 1
            except Exception as e:
                print(f"挂多单失败: {e}")
    
    print(f"挂单完成: {placed} 个")
    return placed


def check_stop():
    """检查止损止盈"""
    price = get_price()
    pos = get_position()
    
    if not pos:
        return False
    
    # 止损
    if price < STOP_LOSS:
        print(f"⚠️ 触发止损: ${price} < ${STOP_LOSS}")
        side = 'SELL' if pos['amount'] > 0 else 'BUY'
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type='MARKET',
                quantity=round(pos['amount'], 3)
            )
            print("✅ 止损平仓")
            return True
        except Exception as e:
            print(f"止损失败: {e}")
    
    # 止盈(可选)
    if price > TAKE_PROFIT:
        print(f"💰 触发止盈: ${price} > ${TAKE_PROFIT}")
        side = 'SELL' if pos['amount'] > 0 else 'BUY'
        try:
            client.futures_create_order(
                symbol=SYMBOL, side=side, type='MARKET',
                quantity=round(pos['amount'], 3)
            )
            print("✅ 止盈平仓")
            return True
        except Exception as e:
            print(f"止盈失败: {e}")
    
    return False


def run():
    print("="*50)
    print("ETH 窄区间网格机器人 v2")
    print(f"区间: ${GRID_LOWER} - ${GRID_UPPER}")
    print(f"网格: {GRID_COUNT} 格, 间距 ${GRID_SIZE:.2f}")
    print(f"止损: ${STOP_LOSS}, 止盈: ${TAKE_PROFIT}")
    print(f"资金: ${TOTAL_USDT}, 杠杆: {LEVERAGE}x")
    print("="*50)
    
    state = load_state()
    
    # 取消旧挂单
    cancel_all()
    
    # 挂新网格
    place_grid()
    
    # 设置杠杆
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except:
        pass
    
    last_check = time.time()
    
    while True:
        try:
            price = get_price()
            pos = get_position()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
            print(f"  价格: ${price}")
            print(f"  持仓: {pos['amount'] if pos else 0} ETH")
            
            # 检查止损止盈
            if check_stop():
                cancel_all()
                state['orders'] = {}
                save_state(state)
                place_grid()
            
            # 检查挂单数量，不够就补
            open_orders = client.futures_get_open_orders(symbol=SYMBOL)
            if len(open_orders) < GRID_COUNT // 2:
                print("补挂单...")
                place_grid()
            
            # 每5分钟检查一次
            time.sleep(300)
            
        except Exception as e:
            print(f"错误: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run()
