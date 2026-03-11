#!/usr/bin/env python3
"""
ETH合约自动交易机器人
5倍杠杆网格策略
"""

import os
import sys
import time
import json
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from binance.client import Client
from small_capital_strategy import SmallCapitalStrategy
from notify import send_message

# 配置
SYMBOL = "ETHUSDT"
CAPITAL = 63
LEVERAGE = 5
CHECK_INTERVAL = 300  # 5分钟检查一次

# 状态文件
STATE_FILE = "/root/.openclaw/workspace/quant/quant/data/eth_grid_state.json"


def load_state():
    """加载状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"position": 0, "entry_price": 0, "orders": 0}


def save_state(state):
    """保存状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_client(testnet=False):
    """获取交易客户端"""
    from config import API_KEY, SECRET_KEY, TESTNET
    
    # 优先使用配置文件
    import yaml
    with open('/root/.openclaw/workspace/quant/quant/config/exchange.yaml') as f:
        config = yaml.safe_load(f)
    
    if testnet:
        api_key = config['binance']['testnet']['api_key']
        secret = config['binance']['testnet']['secret_key']
    else:
        api_key = config['binance']['production']['api_key']
        secret = config['binance']['production']['secret_key']
    
    return Client(api_key, secret, testnet=testnet)


def get_balance(client):
    """获取账户余额"""
    try:
        account = client.futures_account()
        return float(account['totalWalletBalance'])
    except Exception as e:
        print(f"获取余额失败: {e}")
        return 0


def get_position(client, symbol=SYMBOL):
    """获取持仓"""
    try:
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                return {
                    'amount': abs(float(pos['positionAmt'])),
                    'entry_price': float(pos['entryPrice']),
                    'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT',
                    'unrealized': float(pos['unrealizedProfit'])
                }
        return None
    except Exception as e:
        print(f"获取持仓失败: {e}")
        return None


def get_current_price(client):
    """获取当前价格"""
    try:
        ticker = client.get_symbol_ticker(symbol=SYMBOL)
        return float(ticker['price'])
    except Exception as e:
        print(f"获取价格失败: {e}")
        return 0


def open_position(client, side, amount, price=None):
    """开仓"""
    try:
        if price:
            # 限价单
            order = client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type='LIMIT',
                quantity=amount,
                price=price,
                timeInForce='GTC',
                leverage=LEVERAGE
            )
        else:
            # 市价单
            order = client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type='MARKET',
                quantity=amount,
                leverage=LEVERAGE
            )
        
        print(f"✅ 开仓成功: {side} {amount} ETH")
        send_message(f"🔔 开仓: {side} {amount} ETH @ {price or '市价'}")
        return order
    except Exception as e:
        print(f"❌ 开仓失败: {e}")
        return None


def close_position(client, amount):
    """平仓"""
    try:
        # 获取持仓方向
        position = get_position(client)
        if not position:
            return None
        
        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
        
        order = client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type='MARKET',
            quantity=amount
        )
        
        print(f"✅ 平仓成功: {side} {amount} ETH")
        send_message(f"🔔 平仓: {side} {amount} ETH")
        return order
    except Exception as e:
        print(f"❌ 平仓失败: {e}")
        return None


def run():
    """运行交易机器人"""
    print("=" * 50)
    print("ETH合约网格交易机器人启动")
    print(f"模式: {'测试网' if True else '实盘'}")
    print(f"杠杆: {LEVERAGE}x")
    print("=" * 50)
    
    # 初始化客户端
    client = get_client(testnet=False)  # 实盘
    
    # 初始化策略
    strategy = SmallCapitalStrategy(CAPITAL)
    
    # 加载状态
    state = load_state()
    print(f"当前持仓: {state.get('position', 0)} ETH")
    
    # 发送启动通知
    send_message("🤖 ETH网格交易机器人启动\n5倍杠杆 | 63U本金")
    
    while True:
        try:
            # 获取数据
            current_price = get_current_price(client)
            balance = get_balance(client)
            position = get_position(client)
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
            print(f"  价格: ${current_price}")
            print(f"  余额: ${balance:.2f}")
            print(f"  持仓: {position['amount'] if position else 0} ETH")
            
            # 生成信号
            order = strategy.generate_order(
                current_price=current_price,
                positions=position['amount'] if position else 0
            )
            
            print(f"  信号: {order['action']} - {order['reason']}")
            
            # 执行交易
            if order['action'] == 'BUY' and not position:
                # 开多仓
                amount = order['amount'] / current_price
                result = open_position(client, 'BUY', amount)
                if result:
                    state['position'] = amount
                    state['entry_price'] = current_price
                    state['orders'] += 1
                    save_state(state)
            
            elif order['action'] == 'SELL' and position:
                # 平仓
                result = close_position(client, position['amount'])
                if result:
                    state['position'] = 0
                    state['entry_price'] = 0
                    state['orders'] += 1
                    save_state(state)
            
            # 检查止损/止盈
            if position:
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # 止损 -3%
                if pnl_pct <= -0.03:
                    print(f"  ⚠️ 触发止损!")
                    close_position(client, position['amount'])
                    state['position'] = 0
                    save_state(state)
                    send_message(f"🛑 止损! 亏损{pnl_pct:.1%}")
                
                # 止盈 +6%
                elif pnl_pct >= 0.06:
                    print(f"  ✅ 触发止盈!")
                    close_position(client, position['amount'])
                    state['position'] = 0
                    save_state(state)
                    send_message(f"💰 止盈! 盈利{pnl_pct:.1%}")
            
        except Exception as e:
            print(f"错误: {e}")
        
        # 等待
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
