#!/usr/bin/env python3
"""
ETH自适应ATR网格交易机器人 v3
修复版
"""
import time
import yaml
import json
from datetime import datetime
from binance.client import Client
from adaptive_grid_strategy import get_signal
from notify import send_message

# 配置
CONFIG_FILE = 'config/exchange.yaml'
SYMBOL = 'ETHUSDT'
LEVERAGE = 10
CHECK_INTERVAL = 300
REPORT_INTERVAL = 3600

# 风险参数
MAX_POSITION = 0.02  # 最大0.02 ETH
MAX_DAILY_LOSS = 0.05  # 每天最大亏损5%
MAX_TRADES = 20  # 每天最大交易次数

# 加载配置
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

client = Client(
    config['binance']['production']['api_key'],
    config['binance']['production']['secret_key'],
    testnet=False
)

# 启动时设置杠杆
try:
    client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    print(f"✅ 杠杆设置: {LEVERAGE}x")
except Exception as e:
    print(f"杠杆设置: {e}")

# 状态文件
STATE_FILE = 'bot_state.json'


def load_state():
    """加载状态，同时从 Binance 同步持仓"""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except:
        state = {'position': 0, 'entry_price': 0, 'orders': 0, 'side': '', 'daily_trades': 0, 'daily_pnl': 0}
    
    # 从 Binance 同步持仓状态
    try:
        for p in client.futures_position_information(symbol=SYMBOL):
            amt = float(p.get('positionAmt', 0))
            if amt != 0:
                state['position'] = abs(amt)
                state['entry_price'] = float(p.get('entryPrice', 0))
                state['side'] = 'LONG' if amt > 0 else 'SHORT'
                print(f"🔄 同步持仓: {state['position']} ETH @ ${state['entry_price']}")
                break
            else:
                # 无持仓
                if state.get('position', 0) > 0:
                    print("🔄 同步: 无持仓")
                state['position'] = 0
                state['side'] = ''
    except Exception as e:
        print(f"同步持仓失败: {e}")
    
    return state


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def get_price():
    return float(client.get_symbol_ticker(symbol=SYMBOL)['price'])


def get_balance():
    return float(client.futures_account()['totalWalletBalance'])


def get_position():
    for p in client.futures_position_information(symbol=SYMBOL):
        amt = float(p.get('positionAmt', 0))
        if amt != 0:
            return {'amount': abs(amt), 'entry_price': float(p.get('entryPrice', 0)), 'side': 'LONG' if amt > 0 else 'SHORT'}
    return None


def open_position(side, amount):
    """开仓 - side: BUY(多) or SELL(空)"""
    try:
        order = client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type='MARKET',
            quantity=round(amount, 4)
        )
        print(f"✅ {'做多' if side == 'BUY' else '做空'} {amount} ETH")
        return order
    except Exception as e:
        print(f"❌ 开仓失败: {e}")
        return None


def close_position(amount, side):
    """平仓 - side: LONG or SHORT"""
    try:
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        order = client.futures_create_order(
            symbol=SYMBOL,
            side=close_side,
            type='MARKET',
            quantity=round(amount, 4)
        )
        print(f"✅ 平仓 {amount} ETH")
        return order
    except Exception as e:
        print(f"❌ 平仓失败: {e}")
        return None


def run():
    print("="*50)
    print("ETH自适应ATR网格机器人 v3")
    print("="*50)
    
    state = load_state()
    last_report = time.time()
    
    # 初始信息
    info = get_signal()
    send_message(f"🤖 ETH自适应网格v3启动\n" +
                f"价格: ${info['price']:.2f}\n" +
                f"ATR: {info['atr']:.2f} ({info['vol_ratio']:.1f}%)\n" +
                f"网格: {info['grid_size']:.2f}\n" +
                f"趋势: {info['trend']}")
    
    while True:
        try:
            current_price = get_price()
            balance = get_balance()
            position = get_position()
            info = get_signal()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
            print(f"  价格: ${current_price}")
            print(f"  ATR: {info['atr']:.2f} ({info['vol_ratio']:.1f}%)")
            print(f"  网格: {info['grid_size']:.2f}")
            print(f"  趋势: {info['trend']}")
            print(f"  区间: {info['lower_bound']:.0f} - {info['upper_bound']:.0f}")
            print(f"  止损: {info['stop_loss']:.0f}")
            print(f"  余额: ${balance:.2f}")
            print(f"  持仓: {position['amount'] if position else 0}")
            
            # 波动过滤 - 波动太大暂停
            if info['pause_strategy']:
                print("  ⚠️ 波动过大，暂停交易")
            
            # 交易逻辑
            elif not position:
                # 无持仓 - 区间突破策略
                if current_price < info['lower_bound']:
                    # 跌破区间下限 → 做多
                    amount = 21 / current_price
                    if amount <= MAX_POSITION and state.get('daily_trades', 0) < MAX_TRADES:
                        if open_position('BUY', amount):
                            state.update({'position': amount, 'side': 'LONG', 'entry_price': current_price, 'orders': state.get('orders', 0) + 1, 'daily_trades': state.get('daily_trades', 0) + 1})
                            save_state(state)
                            send_message(f"🔔 买入 {amount:.4f} ETH @ ${current_price}\n止损: ${info['stop_loss']:.0f}")
                
                elif current_price > info['upper_bound']:
                    # 突破区间上限 → 做空
                    amount = 21 / current_price
                    if amount <= MAX_POSITION and state.get('daily_trades', 0) < MAX_TRADES:
                        if open_position('SELL', amount):
                            state.update({'position': amount, 'side': 'SHORT', 'entry_price': current_price, 'orders': state.get('orders', 0) + 1, 'daily_trades': state.get('daily_trades', 0) + 1})
                            save_state(state)
                            send_message(f"🔔 做空 {amount:.4f} ETH @ ${current_price}\n止损: ${info['stop_loss']:.0f}")
            else:
                # 有持仓
                entry = state.get('entry_price') or current_price
                if entry == 0:
                    entry = current_price
                if state['side'] == 'LONG':
                    pnl_pct = (current_price - entry) / entry if entry > 0 else 0
                else:
                    pnl_pct = (entry - current_price) / entry if entry > 0 else 0
                
                # 止损
                stop_triggered = (state['side'] == 'LONG' and current_price < info['stop_loss']) or (state['side'] == 'SHORT' and current_price > info['stop_loss'])
                
                if stop_triggered:
                    close_position(state['position'], state['side'])
                    state['position'] = 0
                    state['daily_pnl'] = state.get('daily_pnl', 0) + pnl_pct
                    save_state(state)
                    send_message(f"🛑 止损! 亏损{pnl_pct:.1%}")
                
                # 止盈/区间回归
                elif state['side'] == 'LONG' and current_price > info['upper_bound']:
                    close_position(state['position'], 'LONG')
                    state['position'] = 0
                    state['daily_pnl'] = state.get('daily_pnl', 0) + pnl_pct
                    save_state(state)
                    send_message(f"💰 止盈! 盈利{pnl_pct:.1%}")
                
                elif state['side'] == 'SHORT' and current_price < info['lower_bound']:
                    close_position(state['position'], 'SHORT')
                    state['position'] = 0
                    state['daily_pnl'] = state.get('daily_pnl', 0) + pnl_pct
                    save_state(state)
                    send_message(f"💰 止盈! 盈利{pnl_pct:.1%}")
            
            # 每小时报告
            if time.time() - last_report > REPORT_INTERVAL:
                pos = position['amount'] if position else 0
                pnl = pnl_pct * 100 if position else 0
                daily = state.get('daily_trades', 0)
                send_message(f"📊 状态报告\n" +
                           f"价格: ${current_price}\n" +
                           f"ATR: {info['atr']:.1f} ({info['vol_ratio']:.1f}%)\n" +
                           f"趋势: {info['trend']}\n" +
                           f"持仓: {pos:.4f} ETH\n" +
                           f"盈亏: {pnl:+.1f}%\n" +
                           f"今日交易: {daily}次\n" +
                           f"余额: ${balance:.2f}")
                last_report = time.time()
            
        except Exception as e:
            print(f"错误: {e}")
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
