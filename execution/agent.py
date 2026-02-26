"""
执行Agent - 完整版 (整合风控+仓位管理)
========================================

包含:
- 风控检查 (冷却期/连亏/次数)
- 凯利公式仓位计算
- 交易执行+重试
- 日志记录

作者: AutoQuant
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
    
    def calculate_kelly_position(self, balance, price):
        """凯利公式计算仓位"""
        # 简化版凯利
        win_rate = 0.5
        win_loss_ratio = 2.0
        
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        kelly = max(kelly * 0.25, 0.1)  # 限制
        kelly = min(kelly, MAX_POSITION_PCT)
        
        # 连亏减半
        if self.state.consecutive_losses >= 1:
            kelly = kelly * 0.5
            print(f"  ⚠️ 连亏仓位: {kelly*100:.1f}%")
        
        value = balance * LEVERAGE * kelly
        qty = round(value / price, 3)
        
        return qty, kelly
    
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
            qty, pct = self.calculate_kelly_position(balance, price)
            
            if qty * price < MIN_TRADE_VALUE:
                print(f"⛔ 资金不足")
                return {"status": "blocked", "reason": "资金不足"}
            
            print(f"\n🟢 买入: {qty} BTC ({pct*100:.1f}%)")
            
            for attempt in range(3):
                try:
                    order = self.broker.place_order(self.symbol, "BUY", qty)
                    result = {"status": "success", "side": "BUY", "qty": qty, "order_id": order.get("orderId")}
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
        
        # 有持仓+卖出信号
        elif has_position and signal == "SELL":
            print(f"\n🔴 卖出平仓")
            
            try:
                order = self.broker.close_position(self.symbol)
                result = {"status": "success", "side": "SELL"}
                print(f"✅ 成功!")
                
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
