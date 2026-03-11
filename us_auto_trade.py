#!/usr/bin/env python3
"""
美股自动交易脚本
基于IBKR实盘/模拟账户
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from market_executor import MarketExecutor, MarketType
from signals import generate_signal
from notify import send_message

# 配置
PAPER = True  # True=模拟盘, False=实盘
SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT"]  # 监控的股票
MIN_CONFIDENCE = 0.65  # 最低置信度
POSITION_SIZE = 100  # 每次买入股数
ACCOUNT_HISTORY_FILE = "/root/.openclaw/workspace/quant/quant/logs/us_stock_history.json"

# 日志
LOG_FILE = "/root/.openclaw/workspace/quant/quant/logs/us_trade.log"


def log(msg):
    """日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_history():
    """加载交易历史"""
    if os.path.exists(ACCOUNT_HISTORY_FILE):
        try:
            with open(ACCOUNT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"positions": [], "orders": []}


def save_history(history):
    """保存交易历史"""
    os.makedirs(os.path.dirname(ACCOUNT_HISTORY_FILE), exist_ok=True)
    with open(ACCOUNT_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def check_position(symbol: str, positions: list) -> dict:
    """检查持仓"""
    for pos in positions:
        if pos.get('symbol') == symbol:
            return pos
    return {}


def run():
    """主循环"""
    log("=" * 50)
    log("美股自动交易启动")
    log(f"模式: {'模拟盘' if PAPER else '实盘'}")
    log("=" * 50)
    
    # 连接broker
    executor = MarketExecutor(MarketType.US_STOCK, paper=PAPER)
    
    if not executor.broker:
        log("❌ Broker连接失败")
        return
    
    # 获取账户信息
    balance = executor.get_account_balance()
    log(f"账户余额: {balance}")
    
    # 获取当前持仓
    positions = executor.get_positions()
    log(f"当前持仓: {positions}")
    
    # 加载历史
    history = load_history()
    
    # 检查每个股票
    for symbol in SYMBOLS:
        log(f"\n检查 {symbol}...")
        
        # 获取价格
        price = executor.get_price(symbol)
        if price <= 0:
            log(f"  ⚠️ 无法获取价格")
            continue
        
        log(f"  价格: ${price}")
        
        # 获取信号
        signal = generate_signal(symbol)
        
        if not signal or signal.get('signal') == 'HOLD':
            log(f"  信号: HOLD")
            continue
        
        signal_type = signal.get('signal')
        confidence = signal.get('confidence', 0)
        
        log(f"  信号: {signal_type} (置信度: {confidence:.0%})")
        
        if confidence < MIN_CONFIDENCE:
            log(f"  置信度不足，跳过")
            continue
        
        # 检查持仓
        position = check_position(symbol, positions)
        
        if signal_type == "BUY":
            if position:
                log(f"  已持有 {symbol}，跳过")
            else:
                # 买入
                log(f"  买入 {symbol} x {POSITION_SIZE}")
                order_id = executor.buy(symbol, POSITION_SIZE)
                
                if order_id:
                    log(f"  ✅ 订单成功: {order_id}")
                    history["orders"].append({
                        "time": datetime.now().isoformat(),
                        "symbol": symbol,
                        "action": "BUY",
                        "quantity": POSITION_SIZE,
                        "price": price,
                        "order_id": order_id
                    })
                    send_message(f"🟢 买入 {symbol} x {POSITION_SIZE} @ ${price}")
                else:
                    log(f"  ❌ 订单失败")
        
        elif signal_type == "SELL":
            if not position:
                log(f"  无持仓，跳过")
            else:
                qty = position.get('quantity', POSITION_SIZE)
                # 卖出
                log(f"  卖出 {symbol} x {qty}")
                order_id = executor.sell(symbol, qty)
                
                if order_id:
                    log(f"  ✅ 订单成功: {order_id}")
                    history["orders"].append({
                        "time": datetime.now().isoformat(),
                        "symbol": symbol,
                        "action": "SELL",
                        "quantity": qty,
                        "price": price,
                        "order_id": order_id
                    })
                    send_message(f"🔴 卖出 {symbol} x {qty} @ ${price}")
                else:
                    log(f"  ❌ 订单失败")
    
    # 保存历史
    save_history(history)
    
    # 断开
    executor.disconnect()
    
    log("\n完成")


if __name__ == "__main__":
    run()
