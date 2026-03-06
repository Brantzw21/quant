#!/usr/bin/env python3
"""
自动交易脚本
检测信号并执行交易
"""

import sys
import os
import json
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from light_strategy import generate_signal
from brokers.binance_broker import BinanceBroker
from config import API_KEY, SECRET_KEY, TESTNET, LEVERAGE
from notify import send_message
from risk_logger import log_trade_decision, check_risk_limits
from datetime import datetime
from binance.client import Client

# 交易配置
SYMBOL = "BTCUSDT"
MIN_CONFIDENCE = 0.6  # 最低置信度
POSITION_SIZE = 0.02  # 每次交易数量 (0.02 BTC ≈ $1,500)
STOP_LOSS = 0.03  # 3%止损
TAKE_PROFIT = 0.08  # 8%止盈
LEVERAGE = 3  # 3x杠杆

# 账户历史记录文件
ACCOUNT_HISTORY_FILE = "/root/.openclaw/workspace/quant_v2/logs/account_history.json"

def load_account_history():
    """加载账户历史"""
    if os.path.exists(ACCOUNT_HISTORY_FILE):
        try:
            with open(ACCOUNT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"peak_balance": 0, "records": []}

def save_account_history(history):
    """保存账户历史"""
    os.makedirs(os.path.dirname(ACCOUNT_HISTORY_FILE), exist_ok=True)
    with open(ACCOUNT_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def get_account_info():
    """获取账户信息（含真实回撤）"""
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    account = client.futures_account()
    positions = client.futures_position_information()
    
    # 获取账户余额
    total_balance = float(account.get('totalWalletBalance', 0))
    available_balance = float(account.get('availableBalance', 0))
    unrealized_pnl = float(account.get('totalUnrealizedProfit', 0))
    
    # 当前总权益
    total_equity = total_balance + unrealized_pnl
    
    # 加载历史记录计算回撤
    history = load_account_history()
    peak_balance = history.get('peak_balance', total_equity)
    
    # 更新最高权益
    if total_equity > peak_balance:
        peak_balance = total_equity
        history['peak_balance'] = peak_balance
    
    # 计算回撤
    if peak_balance > 0:
        current_drawdown = (peak_balance - total_equity) / peak_balance * 100
    else:
        current_drawdown = 0
    
    # 记录本次权益
    history['records'].append({
        "timestamp": datetime.now().isoformat(),
        "total_equity": total_equity,
        "unrealized_pnl": unrealized_pnl,
        "drawdown": current_drawdown
    })
    # 只保留最近1000条
    history['records'] = history['records'][-1000:]
    save_account_history(history)
    
    # 检查持仓
    position = 0
    for p in positions:
        if p['symbol'] == SYMBOL and float(p['positionAmt']) != 0:
            position = abs(float(p['positionAmt']))
            break
    
    return {
        "balance": available_balance,
        "total_equity": total_equity,
        "position": position,
        "unrealized_pnl": unrealized_pnl,
        "current_drawdown": current_drawdown,
        "peak_balance": peak_balance
    }

def execute_trade(signal_data):
    """执行交易"""
    signal = signal_data.get('signal', 'HOLD')
    confidence = signal_data.get('confidence', 0)
    price = signal_data.get('indicators', {}).get('4h', {}).get('price', 0)
    
    # 检查置信度
    if confidence < MIN_CONFIDENCE:
        print(f"置信度不足 < {MIN_CONFIDENCE}, 当前: {confidence}")
        return None
    
    # 获取账户信息
    acc = get_account_info()
    
    # 风控检查（使用真实账户数据）
    risk_check = check_risk_limits(
        position_value=acc['position'] * price,
        total_equity=acc['total_equity'],
        current_drawdown=acc['current_drawdown'],
        volatility=0.02  # 可后续从市场数据获取
    )
    
    if not risk_check["passed"]:
        print(f"风控拦截: {risk_check['reasons']}")
        log_trade_decision({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signal": signal,
            "price": price,
            "reason": signal_data.get('reason', ''),
            "risk_checks": risk_check["checks"],
            "result": "REJECTED",
            "reject_reason": risk_check["reasons"]
        })
        return None
    
    # 初始化Broker
    broker = BinanceBroker(API_KEY, SECRET_KEY, testnet=TESTNET)
    
    # 执行交易
    if signal == "BUY" and acc['position'] == 0:
        # 开多
        print(f"执行买入: {POSITION_SIZE} BTC @ ${price}")
        order = broker.place_order(
            symbol=SYMBOL,
            side='BUY',
            quantity=POSITION_SIZE,
            leverage=LEVERAGE
        )
        
        # 记录
        log_trade_decision({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signal": signal,
            "price": price,
            "confidence": confidence,
            "reason": signal_data.get('reason', ''),
            "risk_checks": risk_check["checks"],
            "result": "EXECUTED",
            "order": order.get('orderId') if order else None
        })
        
        # 通知
        msg = f"""
🟢 买入信号执行成功

币种: {SYMBOL}
数量: {POSITION_SIZE} BTC
价格: ${price:,.2f}
置信度: {confidence*100:.0f}%
原因: {signal_data.get('reason', '')}
"""
        send_message(msg)
        return "BUY"
    
    elif signal == "SELL" and acc['position'] > 0:
        # 平仓
        print(f"执行卖出: {acc['position']} BTC @ ${price}")
        order = broker.place_order(
            symbol=SYMBOL,
            side='SELL',
            quantity=acc['position'],
            leverage=LEVERAGE
        )
        
        # 记录
        log_trade_decision({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signal": signal,
            "price": price,
            "confidence": confidence,
            "reason": signal_data.get('reason', ''),
            "risk_checks": risk_check["checks"],
            "result": "EXECUTED",
            "order": order.get('orderId') if order else None
        })
        
        # 通知
        msg = f"""
🔴 卖出信号执行成功

币种: {SYMBOL}
数量: {acc['position']} BTC
价格: ${price:,.2f}
置信度: {confidence*100:.0f}%
原因: {signal_data.get('reason', '')}
"""
        send_message(msg)
        return "SELL"
    
    else:
        print(f"无需交易: signal={signal}, position={acc['position']}")
        return None

def run():
    """运行自动交易"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自动交易启动")
    
    # 生成信号
    signal_data = generate_signal()
    
    if signal_data is None:
        print("生成信号失败")
        return
    
    print(f"当前信号: {signal_data.get('signal')} ({signal_data.get('confidence')})")
    
    # 执行交易
    result = execute_trade(signal_data)
    
    if result:
        print(f"交易完成: {result}")
    else:
        print("未执行交易")

if __name__ == "__main__":
    run()
