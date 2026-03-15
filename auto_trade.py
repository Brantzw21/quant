#!/usr/bin/env python3
"""
自动交易脚本
检测信号并执行交易
"""

import sys
import os
import json
from datetime import datetime

import yaml
from binance.client import Client

sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from light_strategy import generate_signal
from brokers.binance_broker import BinanceBroker
from config import API_KEY, SECRET_KEY, TESTNET
from notify import send_message
from risk_logger import log_trade_decision, check_risk_limits

# 交易配置
SYMBOL = "BTCUSDT"
MIN_CONFIDENCE = 0.6  # 最低置信度
POSITION_SIZE = 0.02  # 每次交易数量 (0.02 BTC ≈ $1,500)
STOP_LOSS = 0.03  # 3%止损
TAKE_PROFIT = 0.08  # 8%止盈
LEVERAGE = 3  # 3x杠杆

BASE_DIR = "/root/.openclaw/workspace/quant/quant"
LOG_DIR = os.path.join(BASE_DIR, "logs")
ACCOUNT_HISTORY_FILE = os.path.join(LOG_DIR, "account_history.json")
TRADE_STATE_FILE = os.path.join(LOG_DIR, "trade_state.json")
STRATEGY_CONFIG_FILE = os.path.join(BASE_DIR, "config", "strategy.yaml")

DEFAULT_EXECUTION_CONFIG = {
    "cooldown_minutes": 60,
    "max_daily_trades": 2,
}


def load_strategy_config():
    """读取策略配置，优先使用 YAML 中的风险限制。"""
    config = DEFAULT_EXECUTION_CONFIG.copy()
    if not os.path.exists(STRATEGY_CONFIG_FILE):
        return config

    try:
        with open(STRATEGY_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        risk = data.get('risk', {})
        config['cooldown_minutes'] = int(risk.get('cooldown_minutes', config['cooldown_minutes']))
        config['max_daily_trades'] = int(risk.get('max_daily_trades', config['max_daily_trades']))
    except Exception as exc:
        print(f"读取策略配置失败，使用默认值: {exc}")

    return config


def load_account_history():
    """加载账户历史"""
    if os.path.exists(ACCOUNT_HISTORY_FILE):
        try:
            with open(ACCOUNT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"peak_balance": 0, "records": []}


def save_account_history(history):
    """保存账户历史"""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(ACCOUNT_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)


def load_trade_state():
    """加载执行状态，避免脚本重启后失去限频记忆。"""
    if os.path.exists(TRADE_STATE_FILE):
        try:
            with open(TRADE_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except Exception:
            state = {}
    else:
        state = {}

    today = datetime.now().strftime('%Y-%m-%d')
    last_trade_date = state.get('last_trade_date', today)
    trades_today = int(state.get('trades_today', 0)) if last_trade_date == today else 0

    return {
        'last_trade_time': float(state.get('last_trade_time', 0)),
        'last_trade_date': today,
        'trades_today': trades_today,
        'last_executed_signal': state.get('last_executed_signal'),
        'last_rejected_reason': state.get('last_rejected_reason', ''),
    }


def save_trade_state(state):
    """保存执行状态。"""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(TRADE_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)


def get_account_info():
    """获取账户信息（含真实回撤）"""
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    account = client.futures_account()
    positions = client.futures_position_information()

    total_balance = float(account.get('totalWalletBalance', 0))
    available_balance = float(account.get('availableBalance', 0))
    unrealized_pnl = float(account.get('totalUnrealizedProfit', 0))
    total_equity = total_balance + unrealized_pnl

    history = load_account_history()
    peak_balance = history.get('peak_balance', total_equity)

    if total_equity > peak_balance:
        peak_balance = total_equity
        history['peak_balance'] = peak_balance

    if peak_balance > 0:
        current_drawdown = (peak_balance - total_equity) / peak_balance * 100
    else:
        current_drawdown = 0

    history['records'].append({
        'timestamp': datetime.now().isoformat(),
        'total_equity': total_equity,
        'unrealized_pnl': unrealized_pnl,
        'drawdown': current_drawdown,
    })
    history['records'] = history['records'][-1000:]
    save_account_history(history)

    position = 0
    for p in positions:
        if p['symbol'] == SYMBOL and float(p['positionAmt']) != 0:
            position = abs(float(p['positionAmt']))
            break

    return {
        'balance': available_balance,
        'total_equity': total_equity,
        'position': position,
        'unrealized_pnl': unrealized_pnl,
        'current_drawdown': current_drawdown,
        'peak_balance': peak_balance,
    }


def reject_trade(signal, price, reason, signal_data=None, risk_checks=None):
    """统一记录被拦截或跳过的交易。"""
    log_trade_decision({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'signal': signal,
        'price': price,
        'confidence': (signal_data or {}).get('confidence', 0),
        'reason': (signal_data or {}).get('reason', ''),
        'risk_checks': risk_checks or {},
        'result': 'REJECTED',
        'reject_reason': reason,
    })


def can_execute_trade(signal, acc, state, exec_config, signal_data, price):
    """执行前门控：冷却、日上限、同向去重。"""
    now = datetime.now()
    now_ts = now.timestamp()

    if signal not in {'BUY', 'SELL'}:
        return False, f'非交易信号: {signal}'

    cooldown_seconds = exec_config['cooldown_minutes'] * 60
    elapsed = now_ts - state['last_trade_time']
    if state['last_trade_time'] > 0 and elapsed < cooldown_seconds:
        remain = int(cooldown_seconds - elapsed)
        return False, f'冷却中，剩余 {remain} 秒'

    if state['trades_today'] >= exec_config['max_daily_trades']:
        return False, f"已达到当日最大交易次数 {exec_config['max_daily_trades']}"

    if signal == 'BUY' and acc['position'] > 0:
        return False, '已有多头持仓，忽略重复买入'

    if signal == 'SELL' and acc['position'] == 0:
        return False, '当前空仓，忽略卖出信号'

    if state.get('last_executed_signal') == signal:
        return False, f'同向信号去重: 上次已执行 {signal}'

    if signal_data.get('confidence', 0) < MIN_CONFIDENCE:
        return False, f"置信度不足 < {MIN_CONFIDENCE}"

    return True, 'ALLOW'


def update_trade_state_after_execution(state, signal, reject_reason=''):
    """更新执行状态。"""
    state['last_trade_date'] = datetime.now().strftime('%Y-%m-%d')
    if reject_reason:
        state['last_rejected_reason'] = reject_reason
        save_trade_state(state)
        return

    state['last_trade_time'] = datetime.now().timestamp()
    state['trades_today'] += 1
    state['last_executed_signal'] = signal
    state['last_rejected_reason'] = ''
    save_trade_state(state)


def execute_trade(signal_data):
    """执行交易"""
    signal = signal_data.get('signal', 'HOLD')
    confidence = signal_data.get('confidence', 0)
    price = signal_data.get('indicators', {}).get('4h', {}).get('price', 0)
    exec_config = load_strategy_config()
    state = load_trade_state()

    acc = get_account_info()

    allow, gate_reason = can_execute_trade(signal, acc, state, exec_config, signal_data, price)
    if not allow:
        print(f"执行门控拦截: {gate_reason}")
        reject_trade(signal, price, gate_reason, signal_data)
        update_trade_state_after_execution(state, signal, reject_reason=gate_reason)
        return None

    risk_check = check_risk_limits(
        position_value=acc['position'] * price,
        total_equity=acc['total_equity'],
        current_drawdown=acc['current_drawdown'],
        volatility=0.02,
    )

    if not risk_check['passed']:
        reject_reason = '风控拦截: ' + '; '.join(risk_check['reasons'])
        print(reject_reason)
        reject_trade(signal, price, reject_reason, signal_data, risk_check['checks'])
        update_trade_state_after_execution(state, signal, reject_reason=reject_reason)
        return None

    broker = BinanceBroker(API_KEY, SECRET_KEY, testnet=TESTNET)

    if signal == 'BUY' and acc['position'] == 0:
        print(f"执行买入: {POSITION_SIZE} BTC @ ${price}")
        order = broker.place_order(
            symbol=SYMBOL,
            side='BUY',
            quantity=POSITION_SIZE,
            leverage=LEVERAGE,
        )
        if not order:
            reject_reason = '下单失败: BUY 返回空结果'
            reject_trade(signal, price, reject_reason, signal_data, risk_check['checks'])
            update_trade_state_after_execution(state, signal, reject_reason=reject_reason)
            return None

        log_trade_decision({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signal': signal,
            'price': price,
            'confidence': confidence,
            'reason': signal_data.get('reason', ''),
            'risk_checks': risk_check['checks'],
            'result': 'EXECUTED',
            'order': order.get('orderId') if order else None,
        })
        update_trade_state_after_execution(state, signal)

        msg = f"""
🟢 买入信号执行成功

币种: {SYMBOL}
数量: {POSITION_SIZE} BTC
价格: ${price:,.2f}
置信度: {confidence*100:.0f}%
原因: {signal_data.get('reason', '')}
"""
        send_message(msg)
        return 'BUY'

    if signal == 'SELL' and acc['position'] > 0:
        print(f"执行卖出: {acc['position']} BTC @ ${price}")
        order = broker.place_order(
            symbol=SYMBOL,
            side='SELL',
            quantity=acc['position'],
            leverage=LEVERAGE,
        )
        if not order:
            reject_reason = '下单失败: SELL 返回空结果'
            reject_trade(signal, price, reject_reason, signal_data, risk_check['checks'])
            update_trade_state_after_execution(state, signal, reject_reason=reject_reason)
            return None

        log_trade_decision({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signal': signal,
            'price': price,
            'confidence': confidence,
            'reason': signal_data.get('reason', ''),
            'risk_checks': risk_check['checks'],
            'result': 'EXECUTED',
            'order': order.get('orderId') if order else None,
        })
        update_trade_state_after_execution(state, signal)

        msg = f"""
🔴 卖出信号执行成功

币种: {SYMBOL}
数量: {acc['position']} BTC
价格: ${price:,.2f}
置信度: {confidence*100:.0f}%
原因: {signal_data.get('reason', '')}
"""
        send_message(msg)
        return 'SELL'

    skip_reason = f"无需交易: signal={signal}, position={acc['position']}"
    print(skip_reason)
    reject_trade(signal, price, skip_reason, signal_data, risk_check['checks'])
    return None


def run():
    """运行自动交易"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自动交易启动")

    signal_data = generate_signal()
    if signal_data is None:
        print('生成信号失败')
        return

    print(f"当前信号: {signal_data.get('signal')} ({signal_data.get('confidence')})")

    result = execute_trade(signal_data)
    if result:
        print(f"交易完成: {result}")
    else:
        print('未执行交易')


if __name__ == '__main__':
    run()
