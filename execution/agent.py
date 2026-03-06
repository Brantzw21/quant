"""
执行Agent - 完整版 (整合风控+仓位管理)
========================================

包含:
- 风控检查 (冷却期/连亏/次数)
- 凯利公式仓位计算
- 交易执行+重试
- 日志记录

作者: LH Quant Team
版本: 2.1
更新: 2026-02-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance.client import Client
from config import *
import json
from datetime import datetime
import time

class RiskState:
    """风控状态"""
    def __init__(self):
        self.trades_today = 0
        self.last_trade_time = 0
        self.consecutive_losses = 0
        self.last_trade_date = ""
        self.is_cooling_down = False
        self.total_pnl = 0
        self.peak_balance = 0  # 峰值余额
        self.max_drawdown = 0.15  # 最大回撤15%触发熔断

class ExecutionAgent:
    """执行Agent - 完整版"""
    
    def __init__(self):
        self.client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        self.symbol = SYMBOL
        self.state = self.load_state()
        self.init_broker()
    
    def init_broker(self):
        """初始化Broker"""
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "brokers"))
        from binance_broker import BinanceBroker
        self.broker = BinanceBroker(API_KEY, SECRET_KEY, testnet=TESTNET)
    
    def load_state(self):
        """加载状态"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "risk_state.json")
        
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                state = RiskState()
                state.__dict__.update(data)
                return state
        
        return RiskState()
    
    def save_state(self):
        """保存状态"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "risk_state.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(self.state.__dict__, f, indent=2)
    
    def load_signal(self):
        """读取信号"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_signal.json")
        
        if not os.path.exists(path):
            return None
        
        with open(path, "r") as f:
            return json.load(f)
    
    def check_risk(self, balance, positions):
        """风控检查"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        # 更新峰值余额
        if balance > self.state.peak_balance:
            self.state.peak_balance = balance
        
        # 回撤检查
        if self.state.peak_balance > 0:
            drawdown = (self.state.peak_balance - balance) / self.state.peak_balance
            if drawdown >= self.state.max_drawdown:
                self.state.is_cooling_down = True
                self.state.last_trade_time = now.timestamp()
                self.save_state()
                return False, f"回撤超过{int(drawdown*100)}%,熔断"
        
        # 重置每日
        if self.state.last_trade_date != today:
            self.state.trades_today = 0
            self.state.last_trade_date = today
        
        # 冷却期
        if self.state.is_cooling_down:
            if now.timestamp() - self.state.last_trade_time > COOLDOWN_MINUTES * 60:
                self.state.is_cooling_down = False
                print("  ✅ 冷却结束")
            else:
                return False, "冷却期"
        
        # 连亏限制
        if self.state.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            self.state.is_cooling_down = True
            self.state.last_trade_time = now.timestamp()
            self.save_state()
            return False, f"连亏{self.state.consecutive_losses}次,冷却"
        
        # 次数限制
        if self.state.trades_today >= MAX_DAILY_TRADES:
            return False, "次数满"
        
        has_position = self.symbol in positions and positions[self.symbol]["quantity"] != 0
        
        return True, {
            "has_position": has_position,
            "trades_today": self.state.trades_today,
            "consecutive_losses": self.state.consecutive_losses,
            "is_cooling": self.state.is_cooling_down
        }
    
    def calculate_kelly_position(self, balance, price, volatility=None):
        """凯利公式计算仓位 - 带波动率调整"""
        # 简化版凯利
        win_rate = 0.5
        win_loss_ratio = 2.0
        
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        kelly = max(kelly * 0.25, 0.1)  # 限制
        kelly = min(kelly, MAX_POSITION_PCT)
        
        # 波动率调整: 高波动减仓
        if volatility and volatility > 0.03:
            kelly = kelly * 0.5  # 高波动减半
            print(f"  ⚠️ 高波动减仓: {kelly*100:.1f}%")
        elif volatility and volatility < 0.015:
            kelly = kelly * 1.2  # 低波动可以加仓
            print(f"  📉 低波动加仓: {kelly*100:.1f}%")
        
        # 连亏减半
        if self.state.consecutive_losses >= 1:
            kelly = kelly * 0.5
            print(f"  ⚠️ 连亏仓位: {kelly*100:.1f}%")
        
        value = balance * LEVERAGE * kelly
        qty = round(value / price, 3)
        
        return qty, kelly
    
    def calculate_trailing_stop(self, entry_price, current_price, atr, regime):
        """计算追踪止损"""
        # 根据市场状态设置追踪幅度
        if regime == 'trend_up':
            trail_pct = 0.05  # 5%
        elif regime == 'volatile':
            trail_pct = 0.10  # 10%
        else:
            trail_pct = 0.03  # 3%
        
        # 使用ATR或百分比
        if atr:
            trail_distance = max(atr * 2, entry_price * trail_pct)
        else:
            trail_distance = entry_price * trail_pct
        
        trailing_stop = entry_price - trail_distance
        return trailing_stop
    
    def log_sl_tp(self, event_type, trade_data):
        """记录止盈止损事件"""
        import os
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "sl_tp_log.json")
        
        try:
            with open(log_file, "r") as f:
                logs = json.load(f)
        except:
            logs = []
        
        logs.append({
            "time": datetime.now().isoformat(),
            "event": event_type,
            **trade_data
        })
        
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
    
    def execute_trade(self, signal_data):
        """执行交易"""
        print(f"\n{'='*50}")
        print(f"💰 Execution Agent - 交易执行")
        print(f"{'='*50}")
        
        signal = signal_data.get("signal", "HOLD")
        
        # 状态
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        has_position = self.symbol in positions and positions[self.symbol]["quantity"] != 0
        
        print(f"\n余额: {balance:.2f} USDT")
        print(f"持仓: {positions.get(self.symbol, {'quantity': 0})}")
        
        # 风控
        allow, info = self.check_risk(balance, positions)
        
        if not allow:
            print(f"\n⛔ 风控阻止: {info}")
            return {"status": "blocked", "reason": info}
        
        print(f"\n🛡️ 风控: 通过 | 今日:{info['trades_today']} | 连亏:{info['consecutive_losses']}")
        
        result = None
        
        # 无持仓+买入信号
        if not has_position and signal == "BUY":
            price = signal_data["indicators"]["1h"]["price"]
            # 获取波动率
            volatility = signal_data.get("market_state", {}).get("volatility", 0.02)
            qty, pct = self.calculate_kelly_position(balance, price, volatility)
            
            # 获取动态止损
            sl_info = signal_data.get("dynamic_stop_loss", {})
            sl_price = sl_info.get("price")
            sl_pct = sl_info.get("pct")
            
            if qty * price < MIN_TRADE_VALUE:
                print(f"⛔ 资金不足")
                return {"status": "blocked", "reason": "资金不足"}
            
            print(f"\n🟢 买入: {qty} BTC ({pct*100:.1f}%)")
            if sl_price:
                print(f"  🛡️ 止损: {sl_price} ({sl_pct}%)")
            
            for attempt in range(3):
                try:
                    order = self.broker.place_order(self.symbol, "BUY", qty)
                    result = {
                        "status": "success",
                        "side": "BUY",
                        "qty": qty,
                        "order_id": order.get("orderId"),
                        "entry_price": price,
                        "stop_loss": sl_price,
                        "stop_loss_pct": sl_pct
                    }
                    print(f"✅ 成功!")
                    
                    # 更新状态
                    self.state.trades_today += 1
                    self.state.last_trade_time = datetime.now().timestamp()
                    self.save_state()
                    break
                except Exception as e:
                    print(f"  ⚠️ 尝试{attempt+1}: {e}")
                    time.sleep(2)
            else:
                result = {"status": "failed", "error": str(e)}
        
        # 有持仓+卖出信号 (盈利保护)
        elif has_position and signal == "SELL":
            # 获取持仓信息
            pos_info = positions.get(self.symbol, {})
            entry_price = pos_info.get("entry_price", 0)
            current_price = float(self.broker.client.get_symbol_ticker(symbol=self.symbol)["price"])
            
            # 盈利保护: 如果在盈利中，提高卖出门槛
            if entry_price > 0:
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct > 0.10:  # 盈利超过10%需要更强信号
                    # 检查是否是极端情况才卖出
                    rsi = signal_data.get("indicators", {}).get("1h", {}).get("rsi", 50)
                    if rsi < 80:  # RSI没到极端不卖
                        print(f"\n🛡️ 盈利保护: {pnl_pct*100:.1f}%, 持有")
                        return {"status": "protected", "reason": "盈利保护"}
            
            # 时间止损: 持仓超过7天强制检查
            # (简化实现: 记录上次交易时间)
            last_trade = self.state.last_trade_time
            if last_trade > 0:
                days_held = (now.timestamp() - last_trade) / 86400
                if days_held > 7 and pnl_pct > 0.05:  # 持仓7天以上且盈利
                    print(f"\n⏰ 时间止损: 持仓{days_held:.0f}天, 盈利{ pnl_pct*100:.1f}%")
            print(f"\n🔴 卖出平仓")
            
            # 获取持仓信息
            pos_info = positions.get(self.symbol, {})
            entry_price = pos_info.get("entry_price", 0)
            
            try:
                order = self.broker.close_position(self.symbol)
                exit_price = float(self.broker.client.get_symbol_ticker(symbol=self.symbol)["price"])
                
                # 计算盈亏
                if entry_price > 0:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = 0
                
                result = {
                    "status": "success",
                    "side": "SELL",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": round(pnl_pct, 2)
                }
                print(f"✅ 成功! 盈亏: {pnl_pct:+.2f}%")
                
                # 记录止盈止损
                self.log_sl_tp("CLOSE_POSITION", result)
                
                self.state.trades_today += 1
                self.state.last_trade_time = datetime.now().timestamp()
                self.save_state()
            except Exception as e:
                result = {"status": "failed", "error": str(e)}
                print(f"❌ 失败: {e}")
        
        else:
            print(f"\n⏸️ 无操作")
            result = {"status": "no_action"}
        
        # 记录
        self.log_trade(signal_data, result)
        
        return result
    
    def log_trade(self, signal, result):
        """记录"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "trades.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        trades = []
        if os.path.exists(path):
            with open(path, "r") as f:
                trades = json.load(f)
        
        trades.append({
            "time": datetime.now().isoformat(),
            "signal": signal.get("signal"),
            "result": result,
            "confidence": signal.get("confidence")
        })
        
        trades = trades[-1000:]
        
        with open(path, "w") as f:
            json.dump(trades, f, indent=2)
        
        print(f"📝 已记录")


def run_execution():
    """运行执行Agent"""
    agent = ExecutionAgent()
    
    signal = agent.load_signal()
    if not signal:
        print("❌ 无信号")
        return
    
    result = agent.execute_trade(signal)
    return result


if __name__ == "__main__":
    run_execution()
