#!/usr/bin/env python3
"""
ETH Grid Bot v7.5
Conservative grid mode with margin guards, duplicate-order protection,
and fill circuit breaker.
"""

import time
import yaml
import threading
import traceback
from collections import deque
from datetime import datetime

import pandas as pd
import requests
from binance.client import Client
from binance import ThreadedWebsocketManager

# ===================== CONFIG =====================
CONFIG_FILE = "config/exchange.yaml"
SYMBOL = "ETHUSDT"
GRID_USDT = 25
MAX_GRIDS = 8
MAX_POSITION = 0.2
MAX_ORDER_QTY = 0.05
ATR_PERIOD = 14
ATR_MULT_MIN = 0.8
ATR_MULT_MAX = 1.0
LEVERAGE = 10
STOP_LOSS_BUFFER = 0.035
GRID_RESET_BUFFER = 0.03
GRID_SHIFT_THRESHOLD = 1.5
LOG_FILE = "grid_v7.log"

# Logic safety guards: keep the original trading style, only block pathological repeats.
MIN_AVAILABLE_BALANCE = 5.0
MAX_MARGIN_USAGE_RATIO = 0.98
MAX_POSITION_NOTIONAL_RATIO = 5.0
MAX_FILLS_PER_10M = 12
FILL_COOLDOWN_SECONDS = 600
SYNC_INTERVAL_SECONDS = 5
SYNC_COOLDOWN_SECONDS = 5
POST_STOP_COOLDOWN_SECONDS = 600
PENDING_ORDER_TTL_SECONDS = 120
STARTUP_BALANCE_FLOOR = 5.0

# ===================== STATE =====================
price_cache = 0
price_cache_time = 0
pos_cache = None
pos_cache_time = 0
orders_cache = None
orders_cache_time = 0
atr_cache = None
atr_cache_time = 0
cooldown_until = 0
grid_sync_cooldown_until = 0
grid_center = None
grid_spacing = None
session_target_orders = None
session_inventory_bucket = None
fill_events = deque()
pending_orders = {}
lock = threading.Lock()

# ===================== API =====================
with open(CONFIG_FILE, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

WEBHOOK_URL = cfg.get("webhook", {}).get("url", "")
WEBHOOK_ENABLED = cfg.get("webhook", {}).get("enabled", False)


def send_webhook(msg):
    if not WEBHOOK_ENABLED or not WEBHOOK_URL:
        return
    try:
        requests.post(
            WEBHOOK_URL,
            json={"msg_type": "text", "content": {"text": msg}},
            timeout=5,
        )
    except Exception:
        pass


client = Client(
    cfg["binance"]["production"]["api_key"],
    cfg["binance"]["production"]["secret_key"],
)

# ===================== UTIL =====================
def log(msg, alert=False):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if alert:
        send_webhook(line)


def order_key(side, price):
    return side, round(float(price), 2)


def purge_fill_events():
    cutoff = time.time() - 600
    while fill_events and fill_events[0] < cutoff:
        fill_events.popleft()


def purge_pending_orders():
    cutoff = time.time() - PENDING_ORDER_TTL_SECONDS
    stale = [key for key, ts in pending_orders.items() if ts < cutoff]
    for key in stale:
        pending_orders.pop(key, None)


# ===================== WS PRICE =====================
def handle_price(msg):
    global price_cache, price_cache_time
    try:
        price_cache = float(msg["c"])
        price_cache_time = time.time()
    except Exception:
        pass


# ===================== USER STREAM =====================
def handle_user(msg):
    global cooldown_until, session_target_orders, session_inventory_bucket
    try:
        event_type = msg.get("e")
        if event_type != "ORDER_TRADE_UPDATE":
            return

        order = msg.get("o", {})
        side = order.get("S")
        raw_price = order.get("p") or order.get("ap") or 0
        key = order_key(side, raw_price) if side else None
        status = order.get("X")

        if key:
            if status in {"NEW", "PARTIALLY_FILLED", "FILLED"}:
                pending_orders[key] = time.time()
            elif status in {"CANCELED", "EXPIRED", "REJECTED"}:
                pending_orders.pop(key, None)

        if status != "FILLED":
            return

        fill_events.append(time.time())
        purge_fill_events()
        invalidate_order_cache()

        # A fill means the active grid changed; rebuild session targets from fresh state
        # instead of restoring the exact same completed level on the next sync pass.
        session_target_orders = None
        session_inventory_bucket = None

        filled_qty = order.get("z") or order.get("q") or "0"
        avg_price = order.get("ap") or raw_price or "0"
        trade_msg = (
            f"成交通知\n"
            f"交易对: {SYMBOL}\n"
            f"方向: {side}\n"
            f"价格: {avg_price}\n"
            f"数量: {filled_qty}\n"
            f"状态: FILLED"
        )
        log(trade_msg, alert=True)

        if len(fill_events) >= MAX_FILLS_PER_10M:
            cooldown_until = max(cooldown_until, time.time() + FILL_COOLDOWN_SECONDS)
            try:
                client.futures_cancel_all_open_orders(symbol=SYMBOL)
                invalidate_order_cache()
                pending_orders.clear()
            except Exception as exc:
                log(f"连成交熔断撤单失败 {exc}")
            log(
                f"触发成交熔断: 10分钟内成交 {len(fill_events)} 次, 冷却 {FILL_COOLDOWN_SECONDS}s",
                alert=True,
            )
    except Exception:
        pass


# ===================== WS THREAD =====================
def ws_thread():
    twm = ThreadedWebsocketManager(
        api_key=cfg["binance"]["production"]["api_key"],
        api_secret=cfg["binance"]["production"]["secret_key"],
    )
    twm.start()
    twm.start_symbol_ticker_socket(callback=handle_price, symbol=SYMBOL)
    twm.start_futures_user_socket(callback=handle_user)
    log("WebSocket started")
    while True:
        time.sleep(1800)


# ===================== PRICE =====================
def get_price():
    if price_cache and time.time() - price_cache_time < 10:
        return price_cache
    return float(client.get_symbol_ticker(symbol=SYMBOL)["price"])


# ===================== POSITION =====================
def get_position():
    global pos_cache, pos_cache_time
    if pos_cache and time.time() - pos_cache_time < 15:
        return pos_cache
    try:
        for pos in client.futures_position_information(symbol=SYMBOL):
            amt = float(pos["positionAmt"])
            if amt != 0:
                pos_cache = {
                    "qty": abs(amt),
                    "signed": amt,
                    "entry": float(pos["entryPrice"]),
                    "notional": abs(float(pos.get("notional", 0) or 0)),
                }
                pos_cache_time = time.time()
                return pos_cache
    except Exception:
        pass
    pos_cache = None
    pos_cache_time = time.time()
    return None


# ===================== ORDERS =====================
def get_orders():
    global orders_cache, orders_cache_time
    if orders_cache is not None and time.time() - orders_cache_time < 5:
        return orders_cache
    try:
        orders_cache = client.futures_get_open_orders(symbol=SYMBOL)
        orders_cache_time = time.time()
    except Exception:
        pass
    return orders_cache or []


# ===================== ACCOUNT =====================
def get_account_balance():
    try:
        balances = client.futures_account_balance()
        for item in balances:
            if item.get("asset") == "USDT":
                return float(item.get("balance", 0) or 0), float(item.get("availableBalance", 0) or 0)
    except Exception:
        pass
    return 0.0, 0.0


# ===================== ATR =====================
def calc_atr():
    global atr_cache, atr_cache_time
    if atr_cache and time.time() - atr_cache_time < 1800:
        return atr_cache
    klines = client.futures_klines(symbol=SYMBOL, interval="1h", limit=ATR_PERIOD + 5)
    df = pd.DataFrame(klines)[[1, 2, 3, 4]]
    df.columns = ["open", "high", "low", "close"]
    df = df.astype(float)
    df["pc"] = df["close"].shift(1)
    df = df.dropna()
    df["tr"] = df.apply(
        lambda row: max(
            row["high"] - row["low"],
            abs(row["high"] - row["pc"]),
            abs(row["low"] - row["pc"]),
        ),
        axis=1,
    )
    atr = df["tr"].ewm(span=ATR_PERIOD).mean().iloc[-1]
    atr_cache = atr
    atr_cache_time = time.time()
    return atr


# ===================== GRID =====================
def refresh_grid_parameters(price, atr, force=False):
    global grid_center, grid_spacing
    if grid_center is None or force:
        grid_center = round(price, 2)
    if grid_spacing is None or force:
        vol = atr / price
        mult = ATR_MULT_MAX if vol > 0.015 else ATR_MULT_MIN
        grid_spacing = round(max(atr * mult, price * 0.012), 2)


def generate_grid(max_levels_per_side):
    grids = []
    for i in range(1, max_levels_per_side + 1):
        buy_price = round(grid_center - i * grid_spacing, 2)
        sell_price = round(grid_center + i * grid_spacing, 2)
        grids.append(("BUY", buy_price))
        grids.append(("SELL", sell_price))
    return grids


# ===================== INVENTORY =====================
def inventory_ratio():
    pos = get_position()
    if not pos:
        return 0
    return pos["signed"] / MAX_POSITION


# ===================== ORDER =====================
def invalidate_order_cache():
    global orders_cache, orders_cache_time
    orders_cache = None
    orders_cache_time = 0


def margin_guard(price):
    total_balance, available_balance = get_account_balance()
    pos = get_position()
    position_notional = pos["notional"] if pos else 0.0

    if available_balance < MIN_AVAILABLE_BALANCE:
        return False, f"可用保证金过低: {available_balance:.2f} USDT"

    if total_balance > 0:
        used_ratio = max(0.0, (total_balance - available_balance) / total_balance)
        position_ratio = position_notional / total_balance
        if used_ratio > MAX_MARGIN_USAGE_RATIO:
            return False, f"保证金占用过高: {used_ratio:.1%}"
        if position_ratio > MAX_POSITION_NOTIONAL_RATIO:
            return False, f"仓位名义价值过高: {position_ratio:.1%}"

    return True, "ALLOW"


def place_order(side, price):
    with lock:
        key = order_key(side, price)
        purge_pending_orders()

        if key in pending_orders:
            log(f"重复挂单拦截 {side} {price}")
            return False

        live_order_keys = {order_key(order['side'], order['price']) for order in get_orders()}
        if key in live_order_keys:
            pending_orders[key] = time.time()
            log(f"已存在同价同向挂单 {side} {price}")
            return False

        allow, reason = margin_guard(price)
        if not allow:
            log(f"下单拦截 {reason}", alert=True)
            return False

        qty = GRID_USDT / price
        if qty > MAX_ORDER_QTY:
            qty = MAX_ORDER_QTY

        pending_orders[key] = time.time()
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type="LIMIT",
                price=round(price, 2),
                quantity=round(qty, 3),
                timeInForce="GTC",
            )
            invalidate_order_cache()
            log(f"挂单 {side} {price}")
            return True
        except Exception as exc:
            pending_orders.pop(key, None)
            log(f"下单失败 {exc}", alert=True)
            return False


def cancel_order(order):
    try:
        client.futures_cancel_order(symbol=SYMBOL, orderId=order["orderId"])
        invalidate_order_cache()
        pending_orders.pop(order_key(order['side'], order['price']), None)
        log(f"撤单 {order['side']} {float(order['price']):.2f}")
        return True
    except Exception as exc:
        log(f"撤单失败 {exc}")
        return False


# ===================== TARGET BUILD =====================
def estimate_max_levels(price):
    total_balance, available_balance = get_account_balance()
    if available_balance <= MIN_AVAILABLE_BALANCE:
        return 1

    usable_balance = max(0.0, min(available_balance - MIN_AVAILABLE_BALANCE, total_balance * MAX_MARGIN_USAGE_RATIO))
    approx_margin_per_order = max((GRID_USDT / LEVERAGE) * 1.3, 2.0)
    affordable_orders = max(1, int(usable_balance / approx_margin_per_order))
    return max(1, min(MAX_GRIDS // 2, affordable_orders // 2 or 1))


def build_target_orders(price, atr, inv):
    refresh_grid_parameters(price, atr)
    max_levels_per_side = estimate_max_levels(price)
    target_orders = []
    for side, grid_price in generate_grid(max_levels_per_side):
        if side == "BUY" and inv > 0.5:
            continue
        if side == "SELL" and inv < -0.5:
            continue
        target_orders.append(order_key(side, grid_price))
    return target_orders


def inventory_bucket(inv):
    if inv >= 0.5:
        return "long_heavy"
    if inv <= -0.5:
        return "short_heavy"
    return "balanced"


def hydrate_session_from_orders(orders):
    global grid_center, grid_spacing, session_target_orders
    if not orders:
        return False

    keyed = sorted({order_key(o["side"], o["price"]) for o in orders}, key=lambda x: x[1])
    buys = sorted([price for side, price in keyed if side == "BUY"])
    sells = sorted([price for side, price in keyed if side == "SELL"])
    if not buys or not sells:
        return False

    nearest_buy = max(buys)
    nearest_sell = min(sells)
    inferred_center = round((nearest_buy + nearest_sell) / 2, 2)

    spacings = []
    for levels in (buys, sells):
        if len(levels) >= 2:
            local = [round(abs(levels[i] - levels[i - 1]), 2) for i in range(1, len(levels))]
            spacings.extend([space for space in local if space > 0])
    inferred_spacing = round(min(spacings), 2) if spacings else round(abs(nearest_sell - nearest_buy) / 2, 2)
    if inferred_spacing <= 0:
        return False

    grid_center = inferred_center
    grid_spacing = inferred_spacing
    session_target_orders = keyed[:MAX_GRIDS]
    return True


def refresh_session_targets(price, atr, inv, force=False):
    global session_target_orders, session_inventory_bucket
    current_bucket = inventory_bucket(inv)
    if session_target_orders is None and not force:
        hydrate_session_from_orders(get_orders())
    if session_target_orders is None or force or session_inventory_bucket != current_bucket:
        session_target_orders = build_target_orders(price, atr, inv)[:MAX_GRIDS]
        session_inventory_bucket = current_bucket
    return session_target_orders


# ===================== GRID ENGINE =====================
def sync_grid():
    global grid_center, grid_spacing, grid_sync_cooldown_until, session_target_orders, session_inventory_bucket
    now = time.time()
    if now < grid_sync_cooldown_until:
        return

    purge_pending_orders()
    price = get_price()
    atr = calc_atr()
    allow, reason = margin_guard(price)
    if not allow:
        log(f"暂停补网格: {reason}")
        return

    refresh_grid_parameters(price, atr)
    reset_threshold = max(atr * GRID_SHIFT_THRESHOLD, price * GRID_RESET_BUFFER)
    inv = inventory_ratio()

    if grid_center and abs(price - grid_center) > reset_threshold:
        old_center = grid_center
        old_spacing = grid_spacing
        refresh_grid_parameters(price, atr, force=True)
        session_target_orders = None
        session_inventory_bucket = None
        log(f"Grid center reset {old_center} -> {grid_center}, spacing {old_spacing} -> {grid_spacing}")

    target_orders = refresh_session_targets(price, atr, inv)[:MAX_GRIDS]
    target_set = set(target_orders)

    orders = get_orders()
    existing_orders = {order_key(o["side"], o["price"]): o for o in orders}
    existing_set = set(existing_orders.keys()) | set(pending_orders.keys())

    to_cancel = [existing_orders[key] for key in sorted(set(existing_orders.keys()) - target_set)]
    to_create = [key for key in target_orders if key not in existing_set]

    changed = False
    for order in to_cancel:
        if cancel_order(order):
            changed = True
            time.sleep(0.2)

    if changed:
        time.sleep(1)

    orders = get_orders()
    existing_set = {order_key(o["side"], o["price"]) for o in orders} | set(pending_orders.keys())
    for side, grid_price in to_create:
        if (side, grid_price) in existing_set:
            continue
        if place_order(side, grid_price):
            changed = True
            existing_set.add((side, grid_price))
            time.sleep(0.2)

    if changed:
        grid_sync_cooldown_until = time.time() + SYNC_COOLDOWN_SECONDS


# ===================== STOP LOSS =====================
def check_stop():
    global cooldown_until, session_target_orders, session_inventory_bucket
    pos = get_position()
    if not pos:
        return

    price = get_price()
    if pos["signed"] > 0:
        stop_price = pos["entry"] * (1 - STOP_LOSS_BUFFER)
        if price <= stop_price:
            side = "SELL"
        else:
            return
    elif pos["signed"] < 0:
        stop_price = pos["entry"] * (1 + STOP_LOSS_BUFFER)
        if price >= stop_price:
            side = "BUY"
        else:
            return
    else:
        return

    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type="MARKET",
            quantity=pos["qty"],
            reduceOnly=True,
        )
        log(f"止损触发 @ {price:.2f}", alert=True)
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
        invalidate_order_cache()
        pending_orders.clear()
        session_target_orders = None
        session_inventory_bucket = None
        cooldown_until = time.time() + POST_STOP_COOLDOWN_SECONDS
    except Exception as exc:
        log(f"止损失败 {exc}", alert=True)


# ===================== EXECUTION =====================
def execution_thread():
    log("Execution started")
    while True:
        try:
            purge_fill_events()
            purge_pending_orders()
            if time.time() < cooldown_until:
                remain = int(cooldown_until - time.time())
                log(f"冷却中 {remain}s")
                time.sleep(10)
                continue
            check_stop()
            sync_grid()
            price = get_price()
            orders = len(get_orders())
            log(f"价格 {price} 挂单 {orders}/{MAX_GRIDS} pending={len(pending_orders)}")
            time.sleep(SYNC_INTERVAL_SECONDS)
        except Exception:
            log(traceback.format_exc(), alert=True)
            time.sleep(30)


# ===================== MAIN =====================
def main():
    total_balance, available_balance = get_account_balance()
    if available_balance < STARTUP_BALANCE_FLOOR:
        log(
            f"启动拒绝: 可用保证金 {available_balance:.2f} USDT < {STARTUP_BALANCE_FLOOR:.2f} USDT",
            alert=True,
        )
        return

    log("Grid Bot v7.5 Start", alert=True)
    try:
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
        invalidate_order_cache()
        pending_orders.clear()
        log("启动前已清理 ETHUSDT 历史挂单")
    except Exception as exc:
        log(f"启动前清理挂单失败 {exc}", alert=True)

    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
    except Exception:
        pass
    threading.Thread(target=ws_thread, daemon=True).start()
    threading.Thread(target=execution_thread, daemon=True).start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
