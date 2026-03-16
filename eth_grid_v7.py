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
import logging
from logging.handlers import RotatingFileHandler
import numpy as np

import requests
from binance.client import Client
from binance import ThreadedWebsocketManager

# ==================== 配置参数 ====================
CONFIG_FILE = "config/exchange.yaml"
SYMBOL = "ETHUSDT"
GRID_USDT = 25
MAX_GRIDS = 7
MAX_POSITION = 0.2
MAX_ORDER_QTY = 0.05
ATR_PERIOD = 14
ATR_MULT_MIN = 1.0
ATR_MULT_MAX = 1.15
LEVERAGE = 10
STOP_LOSS_BUFFER = 0.028
GRID_RESET_BUFFER = 0.015
GRID_SHIFT_THRESHOLD = 1.5
LOG_FILE = "grid_v7.log"

# 风控参数：保持原有交易风格，只阻止极端重复行为
MIN_AVAILABLE_BALANCE = 5.0
MAX_MARGIN_USAGE_RATIO = 0.98
MAX_POSITION_NOTIONAL_RATIO = 1.5
MAX_FILLS_PER_10M = 20
MAX_FILLS_PER_1M = 8
FILL_COOLDOWN_SECONDS = 600
SYNC_INTERVAL_SECONDS = 5
SYNC_COOLDOWN_SECONDS = 5
POST_STOP_COOLDOWN_SECONDS = 600
PENDING_ORDER_TTL_SECONDS = 120
STARTUP_BALANCE_FLOOR = 5.0

# 策略增强参数
DYNAMIC_STOP_TIGHTEN_1 = 0.024
DYNAMIC_STOP_TIGHTEN_2 = 0.02
DYNAMIC_STOP_TIGHTEN_3 = 0.016
TREND_FAST_EMA = 6
TREND_SLOW_EMA = 18
TREND_THRESHOLD = 0.003
TREND_HALT_THRESHOLD = 0.006
DEFENSIVE_MARGIN_RATIO = 0.8
HALT_MARGIN_RATIO = 1.2

# 残仓清理参数
DUST_QTY_THRESHOLD = 0.015
DUST_NOTIONAL_THRESHOLD = 35.0
DUST_PNL_THRESHOLD = 0.8

GRID_MIN_PCT = 0.012
GRID_MAX_PCT = 0.018
GRID_MIN_ABS = 35.0
STRATEGY_CAPITAL_CAP_USDT = 60.0
STRATEGY_CAPITAL_UTILIZATION = 0.8

# ==================== 运行时状态 ====================
# 轻量级缓存/状态，由执行循环和WebSocket回调共享
price_cache = 0
price_cache_time = 0
pos_cache = None
pos_cache_time = 0
orders_cache = None
orders_cache_time = 0
atr_cache = None
atr_cache_time = 0
trend_cache = None
trend_cache_time = 0
cooldown_until = 0
grid_sync_cooldown_until = 0
grid_center = None
grid_spacing = None
risk_state = "NORMAL"
risk_state_reason = "INIT"
trend_halt_active = False
trend_halt_reason = "INIT"
# 会话目标代表当前预期的网格；成交/重置后会重建
session_target_orders = None
session_inventory_bucket = None
fill_events = deque(maxlen=200)  # 限制最大长度，防止无限增长
# 刚提交但可能尚未出现在Binance挂单列表中的订单
pending_orders = {}
pending_lock = threading.RLock()  # 专门保护pending_orders的可重入线程锁，避免嵌套加锁死锁
lock = threading.Lock()

# ==================== API客户端 ====================
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

# ==================== 精度适配 ====================
# 动态获取交易对精度，避免写死导致的精度错误
price_precision = 2
qty_precision = 3
symbol_info_cache = None
symbol_info_cache_time = 0


def load_symbol_info():
    global price_precision, qty_precision, symbol_info_cache, symbol_info_cache_time
    # 缓存1小时
    if symbol_info_cache is not None and time.time() - symbol_info_cache_time < 3600:
        return
    try:
        info = client.futures_exchange_info()
        for sym in info.get("symbols", []):
            if sym.get("symbol") == SYMBOL:
                price_precision = int(sym.get("pricePrecision", 2))
                qty_precision = int(sym.get("quantityPrecision", 3))
                symbol_info_cache = True
                symbol_info_cache_time = time.time()
                log(f"加载交易对精度: price={price_precision}, qty={qty_precision}")
                return
    except Exception:
        pass
    # 失败时使用默认值
    price_precision = 2
    qty_precision = 3


load_symbol_info()


# ==================== 工具函数 ====================
# 配置日志轮转：单文件最大10MB，保留3个备份
logger = logging.getLogger("eth_grid")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(msg, alert=False):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    logger.info(msg)
    if alert:
        send_webhook(line)


def order_key(side, price):
    return side, round_price(price)


def round_qty(qty):
    """动态数量精度处理"""
    return round(qty, qty_precision)


def round_price(price):
    """动态价格精度处理"""
    return round(float(price), price_precision)


def purge_fill_events():
    cutoff = time.time() - 600
    while fill_events and fill_events[0] < cutoff:
        fill_events.popleft()


def purge_pending_orders():
    with pending_lock:
        cutoff = time.time() - PENDING_ORDER_TTL_SECONDS
        stale = [key for key, ts in pending_orders.items() if ts < cutoff]
        for key in stale:
            pending_orders.pop(key, None)


# ==================== WebSocket价格监听 ====================
def handle_price(msg):
    global price_cache, price_cache_time
    try:
        price_cache = float(msg["c"])
        price_cache_time = time.time()
    except Exception:
        pass


# ==================== 用户流监听 ====================
def handle_user(msg):
    global cooldown_until, session_target_orders, session_inventory_bucket
    try:
        # Binance期货用户流是成交/订单状态变更的权威来源
        event_type = msg.get("e")
        if event_type != "ORDER_TRADE_UPDATE":
            return

        order = msg.get("o", {})
        side = order.get("S")
        raw_price = order.get("p") or order.get("ap") or 0
        key = order_key(side, raw_price) if side else None
        status = order.get("X")

        if key:
            # 保持本地重复防护有效，直到Binance确认订单已消失
            with pending_lock:
                if status in {"NEW", "PARTIALLY_FILLED", "FILLED"}:
                    pending_orders[key] = time.time()
                elif status in {"CANCELED", "EXPIRED", "REJECTED"}:
                    pending_orders.pop(key, None)

        if status != "FILLED":
            return

        fill_events.append(time.time())
        purge_fill_events()
        # 成交的订单会使交易所订单快照和内存目标网格都失效
        invalidate_order_cache()

        # 成交意味着活动网格已改变；从新鲜状态重建会话目标
        # 而不是在下一次同步时恢复完全相同的已完成档位
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

        # 成交熔断：同时检查10分钟和1分钟频率，防止极端行情下快速消耗保证金
        recent_1m = [t for t in fill_events if time.time() - t < 60]
        if len(fill_events) >= MAX_FILLS_PER_10M or len(recent_1m) >= MAX_FILLS_PER_1M:
            cooldown_until = max(cooldown_until, time.time() + FILL_COOLDOWN_SECONDS)
            try:
                client.futures_cancel_all_open_orders(symbol=SYMBOL)
                invalidate_order_cache()
                with pending_lock:
                    pending_orders.clear()
            except Exception as exc:
                log(f"连成交熔断撤单失败 {exc}")
            log(
                f"触发成交熔断: 10分钟{len(fill_events)}次/1分钟{len(recent_1m)}次, 冷却 {FILL_COOLDOWN_SECONDS}s",
                alert=True,
            )
    except Exception:
        pass


# ==================== WebSocket线程 ====================
def ws_thread():
    """WebSocket 线程，带自动重连逻辑，防止断线后机器人变盲"""
    global price_cache_time
    twm = None
    while True:
        try:
            # 先停止旧的websocket，防止内存泄漏
            if twm:
                try:
                    twm.stop()
                    log("WebSocket 已停止，准备重连")
                except Exception:
                    pass
                twm = None

            twm = ThreadedWebsocketManager(
                api_key=cfg["binance"]["production"]["api_key"],
                api_secret=cfg["binance"]["production"]["secret_key"],
            )
            twm.start()
            twm.start_symbol_ticker_socket(callback=handle_price, symbol=SYMBOL)
            twm.start_futures_user_socket(callback=handle_user)
            log("WebSocket started")
            # 正常运行时每30秒检查一次连接状态和价格更新
            while True:
                time.sleep(30)
                # 心跳检测：价格超过30秒未更新，说明WebSocket可能假死
                if price_cache_time > 0 and (time.time() - price_cache_time) > 30:
                    log(f"WebSocket 价格心跳超时 {time.time() - price_cache_time:.0f}秒，强制重连")
                    break
        except Exception as e:
            log(f"WebSocket 异常 {e}，5秒后重连...")
            time.sleep(5)
            # 重连前清理可能失效的缓存
            invalidate_order_cache()


# ==================== 价格获取 ====================
def get_price():
    # 优先使用缓存
    if price_cache and time.time() - price_cache_time < 10:
        return price_cache
    # 尝试REST API获取，如果失败则返回缓存值（防止网络闪断导致机器人崩溃）
    try:
        return float(client.get_symbol_ticker(symbol=SYMBOL)["price"])
    except Exception:
        return price_cache if price_cache else 0


# ==================== 仓位查询 ====================
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
                    "pnl": float(pos.get("unRealizedProfit", 0) or 0),
                }
                pos_cache_time = time.time()
                return pos_cache
    except Exception:
        pass
    pos_cache = None
    pos_cache_time = time.time()
    return None


# ==================== 订单查询 ====================
def get_orders():
    global orders_cache, orders_cache_time
    if orders_cache is not None and time.time() - orders_cache_time < 5:
        return orders_cache
    try:
        orders_cache = client.futures_get_open_orders(symbol=SYMBOL)
        orders_cache_time = time.time()
    except Exception:
        # API失败时也要更新cache时间，避免短时间内重复调用
        orders_cache_time = time.time()
        orders_cache = []
    return orders_cache or []


# ==================== 账户查询 ====================
def get_account_balance():
    try:
        balances = client.futures_account_balance()
        for item in balances:
            if item.get("asset") == "USDT":
                return float(item.get("balance", 0) or 0), float(item.get("availableBalance", 0) or 0)
    except Exception:
        pass
    return 0.0, 0.0


def get_strategy_capital():
    total_balance, available_balance = get_account_balance()
    # 风险口径使用真实USDT可用余额，并保留安全冗余和上限保护
    dynamic_capital = max(0.0, available_balance * STRATEGY_CAPITAL_UTILIZATION)
    strategy_total = min(dynamic_capital, STRATEGY_CAPITAL_CAP_USDT)
    strategy_available = strategy_total
    if total_balance <= 0:
        return strategy_total, strategy_available
    return strategy_total, strategy_available


def ensure_protective_exit_order(price, atr):
    pos = get_position()
    if not pos:
        return False

    refresh_grid_parameters(price, atr)
    exit_side = "SELL" if pos["signed"] > 0 else "BUY"
    # 保护单以当前价附近退出为主，避免挂得过远失去保护意义
    raw_target = price + grid_spacing if pos["signed"] > 0 else price - grid_spacing
    target_price = round_price(raw_target)

    orders = get_orders()
    protected = []
    for order in orders:
        if order.get("side") == exit_side and order.get("reduceOnly"):
            protected.append(order)

    for order in protected:
        existing_price = float(order.get("price", 0) or 0)
        existing_qty = float(order.get("origQty", 0) or 0)
        qty_tolerance = max(10 ** (-qty_precision), 1e-9)
        if abs(existing_price - target_price) <= max(price_precision * 0.1, 0.5) and abs(existing_qty - pos["qty"]) < qty_tolerance:
            return False

    for order in protected:
        cancel_order(order)

    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=exit_side,
            type="LIMIT",
            timeInForce="GTC",
            quantity=round_qty(pos["qty"]),
            price=target_price,
            reduceOnly=True,
        )
        invalidate_order_cache()
        log(f"风控保护挂单 {exit_side} {target_price:.2f} qty={pos['qty']:.3f}")
        return True
    except Exception as exc:
        log(f"风控保护挂单失败 {exc}")
        return False


# ==================== ATR计算 ====================
def calc_ema(values, period):
    alpha = 2.0 / (period + 1)
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    return ema


def get_trend_signal():
    global trend_cache, trend_cache_time
    if trend_cache is not None and time.time() - trend_cache_time < 300:
        return trend_cache
    try:
        klines = client.futures_klines(symbol=SYMBOL, interval="1h", limit=TREND_SLOW_EMA + 5)
        closes = np.array([float(k[4]) for k in klines])
        fast = calc_ema(closes[-TREND_FAST_EMA - 5:], TREND_FAST_EMA)
        slow = calc_ema(closes[-TREND_SLOW_EMA - 5:], TREND_SLOW_EMA)
        price = closes[-1]
        spread = (fast - slow) / price if price else 0
        if spread >= TREND_THRESHOLD:
            direction = "UP"
        elif spread <= -TREND_THRESHOLD:
            direction = "DOWN"
        else:
            direction = "FLAT"
        trend_cache = {"direction": direction, "strength": abs(spread)}
        trend_cache_time = time.time()
        return trend_cache
    except Exception:
        pass
    return trend_cache or {"direction": "FLAT", "strength": 0.0}


def dynamic_stop_buffer(pos):
    strategy_total, _ = get_strategy_capital()
    if strategy_total <= 0:
        return STOP_LOSS_BUFFER
    exposure = pos["notional"] / strategy_total
    if exposure >= HALT_MARGIN_RATIO:
        return DYNAMIC_STOP_TIGHTEN_3
    if exposure >= DEFENSIVE_MARGIN_RATIO:
        return DYNAMIC_STOP_TIGHTEN_2
    if exposure >= 0.4:
        return DYNAMIC_STOP_TIGHTEN_1
    return STOP_LOSS_BUFFER


def update_risk_state(price):
    global risk_state, risk_state_reason
    if time.time() < cooldown_until:
        new_state = "COOLDOWN"
        reason = "cooldown"
    else:
        strategy_total, strategy_available = get_strategy_capital()
        pos = get_position()
        position_ratio = (pos["notional"] / strategy_total) if pos and strategy_total > 0 else 0.0
        if strategy_available < MIN_AVAILABLE_BALANCE or position_ratio >= HALT_MARGIN_RATIO:
            new_state = "HALT"
            reason = f"position_ratio={position_ratio:.1%}" if strategy_total > 0 else "low_balance"
        elif position_ratio >= DEFENSIVE_MARGIN_RATIO:
            new_state = "DEFENSIVE"
            reason = f"position_ratio={position_ratio:.1%}"
        else:
            new_state = "NORMAL"
            reason = "normal"
    if new_state != risk_state or reason != risk_state_reason:
        risk_state = new_state
        risk_state_reason = reason
        log(f"风险状态切换 -> {risk_state} ({risk_state_reason})")
    return risk_state


def calc_atr():
    global atr_cache, atr_cache_time
    # ATR缓存10分钟，避免极端行情下网格间距长时间不更新
    if atr_cache and time.time() - atr_cache_time < 600:
        return atr_cache

    klines = client.futures_klines(symbol=SYMBOL, interval="1h", limit=ATR_PERIOD + 5)

    # 使用numpy计算ATR，比pandas更高效
    opens = np.array([float(k[1]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    closes = np.array([float(k[4]) for k in klines])

    pc = closes[:-1]  # 前一根K线的收盘价
    highs = highs[1:]
    lows = lows[1:]
    closes = closes[1:]

    tr = np.maximum(
        highs - lows,
        np.maximum(np.abs(highs - pc), np.abs(lows - pc))
    )

    # 指数加权移动平均计算
    alpha = 2.0 / (ATR_PERIOD + 1)
    atr = tr[0]
    for i in range(1, len(tr)):
        atr = alpha * tr[i] + (1 - alpha) * atr

    atr_cache = atr
    atr_cache_time = time.time()
    return atr


# ==================== 网格参数 ====================
def refresh_grid_parameters(price, atr, force=False):
    global grid_center, grid_spacing
    if grid_center is None or force:
        grid_center = round_price(price)
    if grid_spacing is None or force:
        vol = atr / price
        mult = ATR_MULT_MAX if vol > 0.015 else ATR_MULT_MIN
        # 三重下限：ATR自适应 + 百分比下限 + 绝对下限，避免ETH格距过密
        grid_spacing = round(min(max(atr * mult, price * GRID_MIN_PCT, GRID_MIN_ABS), price * GRID_MAX_PCT), price_precision)


def generate_grid(max_levels_per_side):
    grids = []
    for i in range(1, max_levels_per_side + 1):
        buy_price = round_price(grid_center - i * grid_spacing)
        sell_price = round_price(grid_center + i * grid_spacing)
        grids.append(("BUY", buy_price))
        grids.append(("SELL", sell_price))
    return grids


# ==================== 库存管理 ====================
def inventory_ratio():
    pos = get_position()
    if not pos:
        return 0
    return pos["signed"] / MAX_POSITION


# ==================== 订单操作 ====================
def invalidate_order_cache():
    global orders_cache, orders_cache_time
    orders_cache = None
    orders_cache_time = 0


def margin_guard(price):
    real_total_balance, real_available_balance = get_account_balance()
    strategy_total, strategy_available = get_strategy_capital()
    pos = get_position()
    position_notional = pos["notional"] if pos else 0.0

    if real_available_balance < MIN_AVAILABLE_BALANCE:
        return False, f"可用保证金过低: {real_available_balance:.2f} USDT"

    if strategy_total > 0:
        used_ratio = max(0.0, (strategy_total - strategy_available) / strategy_total)
        position_ratio = position_notional / strategy_total
        if used_ratio > MAX_MARGIN_USAGE_RATIO:
            return False, f"策略保证金占用过高: {used_ratio:.1%}"
        if position_ratio > MAX_POSITION_NOTIONAL_RATIO:
            return False, f"策略仓位名义价值过高: {position_ratio:.1%}"

    return True, "ALLOW"


def place_order(side, price):
    with lock:
        key = order_key(side, price)

        # 第一层：本地pending去重（需要锁保护）
        with pending_lock:
            purge_pending_orders()
            if key in pending_orders:
                log(f"重复挂单拦截 {side} {price}")
                return False

            live_order_keys = {order_key(order['side'], order['price']) for order in get_orders()}
            if key in live_order_keys:
                pending_orders[key] = time.time()
                log(f"已存在同价同向挂单 {side} {price}")
                return False

        # 计算订单数量
        qty = GRID_USDT / price
        if qty > MAX_ORDER_QTY:
            qty = MAX_ORDER_QTY

        # 第二层：仓位硬上限检查，防止MAX_POSITION被突破（检查成交后总量）
        pos = get_position()
        if pos:
            future_pos = abs(pos["signed"]) + qty
            if future_pos > MAX_POSITION:
                log(f"仓位超限: 当前{abs(pos['signed'])}+新单{qty}={future_pos:.4f} > 上限{MAX_POSITION}，禁止加仓")
                return False

        # 第三层：价格偏离保护，防止API返回异常价格
        market_price = get_price()
        if market_price and abs(price - market_price) > grid_spacing * 3:
            log(f"价格偏离过大，跳过挂单: 挂单价={price}, 市场价={market_price}, 阈值={grid_spacing * 3}")
            return False

        allow, reason = margin_guard(price)
        if not allow:
            log(f"下单拦截 {reason}", alert=True)
            return False

        with pending_lock:
            pending_orders[key] = time.time()
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type="LIMIT",
                price=round_price(price),
                quantity=round_qty(qty),
                timeInForce="GTC",
            )
            invalidate_order_cache()
            log(f"挂单 {side} {price}")
            return True
        except Exception as exc:
            with pending_lock:
                pending_orders.pop(key, None)
            log(f"下单失败 {exc}", alert=True)
            return False


def cancel_order(order):
    try:
        client.futures_cancel_order(symbol=SYMBOL, orderId=order["orderId"])
        invalidate_order_cache()
        with pending_lock:
            pending_orders.pop(order_key(order['side'], order['price']), None)
        log(f"撤单 {order['side']} {float(order['price']):.2f}")
        return True
    except Exception as exc:
        log(f"撤单失败 {exc}")
        return False


# ==================== 目标订单构建 ====================
def estimate_max_levels(price):
    strategy_total, strategy_available = get_strategy_capital()
    if strategy_available <= MIN_AVAILABLE_BALANCE:
        return 1

    usable_balance = max(0.0, min(strategy_available - MIN_AVAILABLE_BALANCE, strategy_total * MAX_MARGIN_USAGE_RATIO))
    approx_margin_per_order = max((GRID_USDT / LEVERAGE) * 1.3, 2.0)
    affordable_orders = max(1, int(usable_balance / approx_margin_per_order))
    return max(1, min(MAX_GRIDS // 2, affordable_orders // 2 or 1))


def build_target_orders(price, atr, inv):
    refresh_grid_parameters(price, atr)
    trend = get_trend_signal()
    direction = trend["direction"]
    state = risk_state
    max_levels_per_side = estimate_max_levels(price)
    if state == "DEFENSIVE":
        max_levels_per_side = max(1, max_levels_per_side - 1)

    target_orders = []
    for side, grid_price in generate_grid(max_levels_per_side):
        if side == "BUY" and inv > 0.5:
            continue
        if side == "SELL" and inv < -0.5:
            continue
        # 趋势过滤：强上行减少抄底买入，强下行减少摸顶卖出
        if direction == "UP" and side == "BUY":
            continue
        if direction == "DOWN" and side == "SELL":
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
    inferred_center = round_price((nearest_buy + nearest_sell) / 2)

    spacings = []
    for levels in (buys, sells):
        if len(levels) >= 2:
            local = [round(abs(levels[i] - levels[i - 1]), 2) for i in range(1, len(levels))]
            spacings.extend([space for space in local if space > 0])
    inferred_spacing = round(min(spacings), price_precision) if spacings else round_price(abs(nearest_sell - nearest_buy) / 2)
    if inferred_spacing <= 0:
        return False

    grid_center = inferred_center
    grid_spacing = inferred_spacing
    session_target_orders = keyed[:MAX_GRIDS]
    return True


def refresh_session_targets(price, atr, inv, force=False):
    global session_target_orders, session_inventory_bucket
    current_bucket = inventory_bucket(inv)
    # 新会话时，尝试从实时交易所订单推断当前活动网格
    if session_target_orders is None and not force:
        hydrate_session_from_orders(get_orders())
    if session_target_orders is None or force or session_inventory_bucket != current_bucket:
        session_target_orders = build_target_orders(price, atr, inv)[:MAX_GRIDS]
        session_inventory_bucket = current_bucket
    return session_target_orders


# ==================== 网格引擎 ====================
def sync_grid():
    global grid_center, grid_spacing, grid_sync_cooldown_until, session_target_orders, session_inventory_bucket, trend_halt_active, trend_halt_reason
    now = time.time()
    if now < grid_sync_cooldown_until:
        return

    purge_pending_orders()
    price = get_price()
    atr = calc_atr()
    trend = get_trend_signal()
    trend_halt = trend["direction"] in {"UP", "DOWN"} and trend["strength"] >= TREND_HALT_THRESHOLD
    reason = f"trend={trend['direction']} strength={trend['strength']:.2%}"
    if trend_halt != trend_halt_active or reason != trend_halt_reason:
        trend_halt_active = trend_halt
        trend_halt_reason = reason
        log(f"趋势停机 {'开启' if trend_halt_active else '关闭'} ({trend_halt_reason})")

    state = update_risk_state(price)
    allow, guard_reason = margin_guard(price)
    if trend_halt_active:
        log(f"暂停补网格: 趋势停机 {trend_halt_reason}")
        ensure_protective_exit_order(price, atr)
        return
    if state in {"HALT", "COOLDOWN"} or not allow:
        log(f"暂停补网格: {guard_reason if not allow else state}")
        ensure_protective_exit_order(price, atr)
        return

    refresh_grid_parameters(price, atr)
    reset_threshold = max(atr * GRID_SHIFT_THRESHOLD, price * GRID_RESET_BUFFER)
    inv = inventory_ratio()

    if grid_center and abs(price - grid_center) > reset_threshold:
        old_center = grid_center
        old_spacing = grid_spacing
        refresh_grid_parameters(price, atr, force=True)
        # 大幅漂移意味着旧网格已过时；丢弃会话目标并围绕新中心重建
        session_target_orders = None
        session_inventory_bucket = None
        log(f"Grid center reset {old_center} -> {grid_center}, spacing {old_spacing} -> {grid_spacing}")

    target_orders = refresh_session_targets(price, atr, inv)[:MAX_GRIDS]
    target_set = set(target_orders)

    orders = get_orders()
    existing_orders = {order_key(o["side"], o["price"]): o for o in orders}
    existing_set = set(existing_orders.keys()) | set(pending_orders.keys())

    # 将预期网格与当前实时/待处理订单对比，仅应用增量变化
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
    # 止损仅针对净持仓评估；本脚本假设单向持仓模式
    pos = get_position()
    if not pos:
        return

    price = get_price()
    stop_buffer = dynamic_stop_buffer(pos)
    if pos["signed"] > 0:
        stop_price = pos["entry"] * (1 - stop_buffer)
        if price <= stop_price:
            side = "SELL"
        else:
            return
    elif pos["signed"] < 0:
        stop_price = pos["entry"] * (1 + stop_buffer)
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
            quantity=round_qty(pos["qty"]),
            reduceOnly=True,
        )
        log(f"止损触发 @ {price:.2f} buffer={stop_buffer:.2%}", alert=True)
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
        invalidate_order_cache()
        with pending_lock:
            pending_orders.clear()
        session_target_orders = None
        session_inventory_bucket = None
        cooldown_until = time.time() + POST_STOP_COOLDOWN_SECONDS
    except Exception as exc:
        log(f"止损失败 {exc}", alert=True)


def check_dust_position():
    global session_target_orders, session_inventory_bucket
    pos = get_position()
    if not pos:
        return False

    if risk_state not in {"DEFENSIVE", "HALT"}:
        return False

    if pos["qty"] > DUST_QTY_THRESHOLD:
        return False
    if pos["notional"] > DUST_NOTIONAL_THRESHOLD:
        return False
    if abs(pos.get("pnl", 0.0)) > DUST_PNL_THRESHOLD:
        return False

    side = "SELL" if pos["signed"] > 0 else "BUY"
    price = get_price()
    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type="MARKET",
            quantity=round_qty(pos["qty"]),
            reduceOnly=True,
        )
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
        invalidate_order_cache()
        with pending_lock:
            pending_orders.clear()
        session_target_orders = None
        session_inventory_bucket = None
        log(
            f"残仓清理触发 side={side} qty={pos['qty']:.3f} notional={pos['notional']:.2f} pnl={pos.get('pnl', 0.0):.2f} price={price:.2f}",
            alert=True,
        )
        return True
    except Exception as exc:
        log(f"残仓清理失败 {exc}", alert=True)
        return False


# ==================== 执行主循环 ====================
def execution_thread():
    log("执行线程已启动")
    while True:
        try:
            # 主循环顺序：冷却检查 -> 止损 -> 网格同步 -> 状态快照
            purge_fill_events()
            purge_pending_orders()
            if time.time() < cooldown_until:
                remain = int(cooldown_until - time.time())
                log(f"冷却中 {remain}s")
                time.sleep(10)
                continue
            check_stop()
            check_dust_position()
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
        with pending_lock:
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
