"""
LH Quant v2.0 - 完整版
=========================

整合所有能力:
- 策略Agent: 市场分析+信号生成
- 执行Agent: 交易+风控+仓位
- 监控Agent: 系统健康+异常检测
- 回测模块: 历史数据测试

作者: AutoQuant
"""

import sys
import os
import time
import builtins
import json
from datetime import datetime

# 保存内置模块
_signal = builtins.__dict__.get('signal')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *

# 恢复 signal
if _signal:
    builtins.signal = _signal

import signal as _signal_module

from strategy.agent import StrategyAgent
from execution.agent import ExecutionAgent

# ==================== 监控Agent ====================

class MonitorAgent:
    """监控Agent - 系统健康检查"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def check_process(self):
        """检查进程"""
        import subprocess
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        
        running = "quant_v2" in result.stdout
        print(f"  进程: {'✅' if running else '❌'}")
        return running
    
    def check_balance(self):
        """检查余额"""
        try:
            from brokers.binance_broker import BinanceBroker
            broker = BinanceBroker(API_KEY, SECRET_KEY, testnet=TESTNET)
            balance = broker.get_balance()
            print(f"  余额: {balance:.2f} USDT")
            return True
        except Exception as e:
            print(f"  余额: ❌ {e}")
            return False
    
    def check_positions(self):
        """检查持仓"""
        try:
            from brokers.binance_broker import BinanceBroker
            broker = BinanceBroker(API_KEY, SECRET_KEY, testnet=TESTNET)
            positions = broker.get_positions()
            has_pos = SYMBOL in positions and positions[SYMBOL]["quantity"] != 0
            print(f"  持仓: {'✅ ' + str(positions.get(SYMBOL, {})) if has_pos else '❌ 无'}")
            return True
        except Exception as e:
            print(f"  持仓: ❌ {e}")
            return False
    
    def check_logs(self):
        """检查日志"""
        log_path = os.path.join(self.base_dir, "logs", "trades.json")
        
        if not os.path.exists(log_path):
            print(f"  日志: ❌ 无")
            return False
        
        with open(log_path, "r") as f:
            trades = json.load(f)
        
        if trades:
            last = trades[-1]
            print(f"  最近: {last.get('signal')} @ {last.get('time', '')[:19]}")
        
        return True
    
    def check_signal(self):
        """检查信号"""
        sig_path = os.path.join(self.base_dir, "data", "last_signal.json")
        
        if not os.path.exists(sig_path):
            print(f"  信号: ❌ 无")
            return False
        
        with open(sig_path, "r") as f:
            sig = json.load(f)
        
        print(f"  信号: {sig.get('signal')} ({sig.get('confidence', 0):.0%})")
        return True
    
    def run(self):
        """运行监控"""
        print(f"\n{'='*50}")
        print(f"🔧 Monitor Agent - 系统监控")
        print(f"{'='*50}")
        
        checks = {
            "进程": self.check_process(),
            "余额": self.check_balance(),
            "持仓": self.check_positions(),
            "日志": self.check_logs(),
            "信号": self.check_signal()
        }
        
        all_ok = all(checks.values())
        
        print(f"\n状态: {'✅ 正常' if all_ok else '⚠️ 异常'}")
        
        return all_ok


# ==================== 回测模块 ====================

class BacktestAgent:
    """回测Agent"""
    
    def __init__(self):
        from binance.client import Client
        self.client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    
    def run(self, days=30):
        """运行回测"""
        print(f"\n{'='*50}")
        print(f"📈 Backtest Agent - 回测")
        print(f"{'='*50}")
        
        # 获取历史数据
        klines = self.client.get_klines(
            symbol=SYMBOL,
            interval="1h",
            limit=days*24
        )
        
        data = [{"close": float(k[4])} for k in klines]
        
        print(f"数据: {len(data)} 条")
        
        # 简化回测
        capital = 10000
        position = 0
        
        trades = 0
        wins = 0
        losses = 0
        
        # 使用策略信号
        strategy = StrategyAgent()
        
        for i in range(50, len(data)):
            hist = data[:i+1]
            
            # 简化信号
            closes = [d["close"] for d in hist]
            ma10 = sum(closes[-10:]) / 10
            ma20 = sum(closes[-20:]) / 20
            
            price = closes[-1]
            
            if position == 0 and ma10 > ma20:  # 金叉买入
                position = capital * 0.9 / price
                capital -= position * price
                trades += 1
                print(f"  买入 @ {price:.2f}")
            
            elif position > 0 and ma10 < ma20:  # 死叉卖出
                capital += position * price
                pnl = (price - (capital / (1-0.9))) / (capital / (1-0.9)) * 100
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                print(f"  卖出 @ {price:.2f} ({pnl:+.1f}%)")
                position = 0
        
        # 最终
        if position > 0:
            capital += position * data[-1]["close"]
        
        total_return = (capital - 10000) / 10000 * 100
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        
        print(f"\n结果:")
        print(f"  收益: {total_return:+.2f}%")
        print(f"  交易: {trades}次")
        print(f"  胜率: {win_rate:.1f}%")
        
        return {
            "return": total_return,
            "trades": trades,
            "win_rate": win_rate
        }


# ==================== 主程序 ====================

running = True

def signal_handler(sig, frame):
    global running
    print("\n🛑 停止...")
    running = False

def main():
    global running
    _signal_module.signal(_signal_module.SIGINT, signal_handler)
    _signal_module.signal(_signal_module.SIGTERM, signal_handler)
    
    print("""
╔══════════════════════════════════════════════╗
║         LH Quant v2.0 完整版              ║
║         策略+执行+监控+回测                 ║
╚══════════════════════════════════════════════╝
    """)
    
    iteration = 0
    
    while running:
        iteration += 1
        
        print(f"\n{'#'*60}")
        print(f"第 {iteration} 轮 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")
        
        try:
            # 1. 策略
            print("\n[1/3] 📊 策略Agent...")
            strategy = StrategyAgent()
            signal_data = strategy.generate_signal()
            strategy.save_signal(signal_data)
            
            # 2. 执行
            print("\n[2/3] 💰 执行Agent...")
            executor = ExecutionAgent()
            executor.execute_trade(signal_data)
            
            # 3. 监控
            print("\n[3/3] 🔧 监控Agent...")
            monitor = MonitorAgent()
            monitor.run()
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        
        if running:
            print(f"\n⏳ 等待 {CHECK_INTERVAL}秒...")
            time.sleep(CHECK_INTERVAL)
    
    print("\n👋 退出")

def cmd_monitor():
    """单独运行监控"""
    MonitorAgent().run()

def cmd_backtest():
    """单独运行回测"""
    BacktestAgent().run()

def cmd_status():
    """查看状态"""
    MonitorAgent().run()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    
    if args.monitor:
        cmd_monitor()
    elif args.backtest:
        cmd_backtest()
    elif args.status:
        cmd_status()
    elif args.once:
        # 单次
        strategy = StrategyAgent()
        signal_data = strategy.generate_signal()
        strategy.save_signal(signal_data)
        
        executor = ExecutionAgent()
        executor.execute_trade(signal_data)
    else:
        main()
