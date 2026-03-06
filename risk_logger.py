"""
交易风控日志模块
记录每笔交易的决策原因和风控检查结果
"""

import json
import os
from datetime import datetime

LOG_DIR = "/root/.openclaw/workspace/quant/quant/logs"
TRADE_LOG_FILE = os.path.join(LOG_DIR, "trade_decisions.json")

def log_trade_decision(decision: dict):
    """
    记录交易决策
    
    decision = {
        "timestamp": "2026-03-04 12:00:00",
        "signal": "BUY",
        "price": 70000,
        "reason": "MACD金叉+RSI超卖",
        "risk_checks": {
            "leverage_check": "PASS",
            "position_size_check": "PASS", 
            "drawdown_check": "PASS",
            "volatility_check": "WARNING"
        },
        "result": "EXECUTED" 或 "REJECTED"
    }
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 读取现有日志
    logs = []
    if os.path.exists(TRADE_LOG_FILE):
        try:
            with open(TRADE_LOG_FILE, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
    
    # 添加新记录
    logs.append(decision)
    
    # 只保留最近1000条
    logs = logs[-1000:]
    
    # 保存
    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def get_trade_history(limit: int = 50):
    """获取交易历史"""
    if not os.path.exists(TRADE_LOG_FILE):
        return []
    
    with open(TRADE_LOG_FILE, 'r') as f:
        logs = json.load(f)
    
    return logs[-limit:]

def check_risk_limits(position_value: float, total_equity: float, current_drawdown: float, volatility: float) -> dict:
    """
    风控检查
    
    返回: {
        "passed": True/False,
        "checks": {
            "leverage": "PASS/REJECT",
            "position_size": "PASS/WARNING/REJECT",
            "drawdown": "PASS/WARNING/REJECT",
            "volatility": "PASS/WARNING"
        },
        "reasons": ["原因1", "原因2"]
    }
    """
    checks = {}
    reasons = []
    
    # 1. 仓位检查 (不超过50%仓位)
    position_pct = position_value / total_equity if total_equity > 0 else 0
    if position_pct > 0.5:
        checks["position_size"] = "REJECT"
        reasons.append(f"仓位过重: {position_pct*100:.1f}%")
    elif position_pct > 0.3:
        checks["position_size"] = "WARNING"
        reasons.append(f"仓位较高: {position_pct*100:.1f}%")
    else:
        checks["position_size"] = "PASS"
    
    # 2. 回撤检查 (不超过20%)
    if abs(current_drawdown) > 20:
        checks["drawdown"] = "REJECT"
        reasons.append(f"回撤过大: {abs(current_drawdown):.1f}%")
    elif abs(current_drawdown) > 10:
        checks["drawdown"] = "WARNING"
        reasons.append(f"回撤较大: {abs(current_drawdown):.1f}%")
    else:
        checks["drawdown"] = "PASS"
    
    # 3. 波动率检查
    if volatility > 0.05:  # 5%
        checks["volatility"] = "WARNING"
        reasons.append(f"波动率高: {volatility*100:.1f}%")
    else:
        checks["volatility"] = "PASS"
    
    # 4. 杠杆检查 (不超过10x)
    # 已在broker层控制
    
    passed = all(c != "REJECT" for c in checks.values())
    
    return {
        "passed": passed,
        "checks": checks,
        "reasons": reasons,
        "metrics": {
            "position_pct": position_pct,
            "drawdown": current_drawdown,
            "volatility": volatility
        }
    }

if __name__ == "__main__":
    # 测试
    result = check_risk_limits(1000, 5000, 5, 0.02)
    print(result)
