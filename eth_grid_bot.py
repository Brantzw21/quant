#!/usr/bin/env python3
"""
ETH 网格交易机器人
用户策略: $1736-$2199 区间, 10格, 止损$1700
"""
import time
import yaml
import json
from datetime import datetime
from binance.client import Client
from notify import send_message

# 配置
CONFIG_FILE = 'config/exchange.yaml'
SYMBOL = 'ETHUSDT'
LEVERAGE = 10
CHECK_INTERVAL = 60  # 每分钟检查

# 网格参数 - 动态网格
GRID_BOTTOM = 1736  # 历史底部
GRID_TOP = 2199    # 历史顶部
GRID_COUNT = 10
STOP_LOSS = 1700
PRICE_RANGE = 0.05  # 只挂当前价格±5%范围内的单

# 每格数量
USDT_PER_GRID = 20  # 每格20U

# 加载配置
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

client = Client(
    config['binance']['testnet']['api_key'],
    config['binance']['testnet']['secret_key'],
    testnet=True
)

# 状态文件
STATE_FILE = 'grid_bot_state.json'


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {
            'grid_orders': {},  # {price: {side, qty, filled}}
            'position': 0,
            'entry_price': 0,
            'total_pnl': 0
        }


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
                'entry_price': float(p.get('entryPrice', 0)),
                'side': 'LONG' if amt > 0 else 'SHORT',
                'pnl': float(p.get('unrealizedProfit', 0))
            }
    return None


def cancel_all_orders():
    """取消所有挂单"""
    orders = client.futures_get_open_orders(symbol=SYMBOL)
    for o in orders:
        client.futures_cancel_order(symbol=SYMBOL, orderId=o['orderId'])
    print(f"取消 {len(orders)} 个挂单")


def place_grid_orders(state):
    """挂网格单 - 只挂当前价格±5%范围内"""
    current_price = get_price()
    placed = 0
    
    # 动态计算网格范围
    lower = current_price * (1 - PRICE_RANGE)
    upper = current_price * (1 + PRICE_RANGE)
    grid_size = (upper - lower) / GRID_COUNT
    
    print(f"挂单范围: ${lower:.2f} - ${upper:.2f}")
    
    for i in range(GRID_COUNT + 1):
        grid_price = round(lower + i * grid_size, 2)
        
        # 检查是否已挂单
        if str(grid_price) in state['grid_orders']:
            continue
        
        qty = max(USDT_PER_GRID / grid_price, 0.001)
        qty = round(qty, 3)
        
        # 买单 (低于当前价格) - 做空单
        if grid_price < current_price:
            try:
                order = client.futures_create_order(
                    symbol=SYMBOL,
                    side='SELL',
                    type='LIMIT',
                    quantity=qty,
                    price=grid_price,
                    timeInForce='GTC',
                    positionSide='BOTH'
                )
                state['grid_orders'][str(grid_price)] = {
                    'side': 'SELL',
                    'qty': qty,
                    'order_id': order['orderId']
                }
                placed += 1
                print(f"挂空单: ${grid_price} x {qty:.3f}")
            except Exception as e:
                print(f"挂空单失败: {e}")
        
        # 卖单 (高于当前价格) - 做多单
        else:
            try:
                order = client.futures_create_order(
                    symbol=SYMBOL,
                    side='BUY',
                    type='LIMIT',
                    quantity=qty,
                    price=grid_price,
                    timeInForce='GTC',
                    positionSide='BOTH'
                )
                state['grid_orders'][str(grid_price)] = {
                    'side': 'BUY',
                    'qty': qty,
                    'order_id': order['orderId']
                }
                placed += 1
                print(f"挂多单: ${grid_price} x {qty:.3f}")
            except Exception as e:
                print(f"挂多单失败: {e}")
    
    if placed > 0:
        save_state(state)
        print(f"✅ 挂单完成: {placed} 个")


def check_filled_orders(state):
    """检查成交并更新状态"""
    current_price = get_price()
    position = get_position()
    
    total_pnl = 0
    
    # 查询所有订单状态
    open_orders = client.futures_get_open_orders(symbol=SYMBOL)
    open_prices = {str(round(float(o['price']), 2)): o['orderId'] for o in open_orders}
    
    # 清理已成交/取消的订单
    to_remove = []
    for price_str, info in state['grid_orders'].items():
        if price_str not in open_prices:
            # 订单已成交或取消
            to_remove.append(price_str)
            if position:
                print(f"订单成交/取消: ${price_str}")
    
    for p in to_remove:
        del state['grid_orders'][p]
    
    save_state(state)
    return position


def check_stop_loss(current_price, position):
    """检查止损"""
    if position and current_price < STOP_LOSS:
        print(f"⚠️ 触发止损: ${current_price} < ${STOP_LOSS}")
        # 市价平仓
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side='SELL' if position['amount'] > 0 else 'BUY',
                type='MARKET',
                quantity=round(position['amount'], 4),
                positionSide='LONG' if position['amount'] > 0 else 'SHORT'
            )
            print("✅ 止损平仓")
            return True
        except Exception as e:
            print(f"止损失败: {e}")
    return False


def run():
    print("="*50)
    print("ETH 网格交易机器人")
    print(f"区间: ${GRID_BOTTOM} - ${GRID_TOP}")
    print(f"网格: {GRID_COUNT} 格 x ${USDT_PER_GRID}")
    print(f"止损: ${STOP_LOSS}")
    print("="*50)
    
    state = load_state()
    last_report = time.time()
    
    # 取消旧挂单
    cancel_all_orders()
    
    # 挂新网格
    place_grid_orders(state)
    
    send_message(f"🤖 ETH网格机器人启动\n" +
                f"区间: ${GRID_BOTTOM} - ${GRID_TOP}\n" +
                f"网格: {GRID_COUNT}格\n" +
                f"止损: ${STOP_LOSS}")
    
    while True:
        try:
            current_price = get_price()
            position = get_position()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
            print(f"  价格: ${current_price}")
            print(f"  持仓: {position['amount'] if position else 0} ETH")
            print(f"  挂单数: {len(state['grid_orders'])}")
            
            # 检查止损
            if check_stop_loss(current_price, position):
                # 止损后重新挂单
                cancel_all_orders()
                state = load_state()
                state['grid_orders'] = {}
                save_state(state)
                place_grid_orders(state)
                send_message(f"🛑 止损触发! 价格: ${current_price}")
            
            # 检查成交
            check_filled_orders(state)
            
            # 检查是否需要补单
            if len(state['grid_orders']) < GRID_COUNT:
                place_grid_orders(state)
            
            # 每小时报告
            if time.time() - last_report > 3600:
                pos = position['amount'] if position else 0
                pnl = position['pnl'] if position else 0
                send_message(f"📊 网格状态\n" +
                           f"价格: ${current_price}\n" +
                           f"持仓: {pos:.4f} ETH\n" +
                           f"盈亏: ${pnl:.2f}\n" +
                           f"挂单: {len(state['grid_orders'])}个")
                last_report = time.time()
            
        except Exception as e:
            print(f"错误: {e}")
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
