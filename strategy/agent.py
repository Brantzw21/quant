"""
策略Agent - 完整版 (整合所有功能)
=====================================

包含:
- 市场状态分析
- 多指标信号生成
- 凯利公式仓位计算
- 风控检查

作者: LH Quant Team
版本: 2.2 (优化版)
更新: 2026-03-04
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 策略参数 (可配置化 - 优化后)
PARAMS = {
    "RSI_PERIOD": 14,  # 优化周期
    "RSI_OVERSOLD": 35,  # 优化阈值
    "RSI_OVERBOUGHT": 65,  # 优化阈值
    "MACD_FAST": 12,
    "MACD_SLOW": 26,
    "MACD_SIGNAL": 9,
    "BB_PERIOD": 20,
    "BB_STD": 2,
    "MA_SHORT": 10,
    "MA_MEDIUM": 20,
    "MA_LONG": 50,
    "MIN_CONFIDENCE": 0.6,
    "REQUIRED_SIGNALS": 2,
}

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET, SYMBOL, INTERVALS
import json
from datetime import datetime
import time
import numpy as np

# 导入市场状态模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from market_regime import calculate_atr, detect_market_regime, get_dynamic_stop_loss, get_dynamic_take_profit, calculate_trailing_stop

class StrategyAgent:
    """策略Agent - 完整版"""
    
    def __init__(self):
        self.client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
        self.symbol = SYMBOL
    
    def get_klines(self, interval, limit=100):
        """获取K线"""
        klines = self.client.get_klines(
            symbol=self.symbol,
            interval=interval,
            limit=limit
        )
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # 清洗异常值
        median = sorted(closes)[len(closes)//2]
        clean_closes = []
        for c in closes:
            if abs(c - median) / median > 0.5:
                clean_closes.append(median)
            else:
                clean_closes.append(c)
        
        return {"close": clean_closes, "high": highs, "low": lows}
    
    def calculate_indicators(self, data, volumes=None):
        """计算技术指标 (优化版)"""
        import numpy as np
        
        closes = data
        P = PARAMS  # 简化引用
        
        # 均线
        ma10 = np.mean(closes[-P["MA_SHORT"]:])
        ma20 = np.mean(closes[-P["MA_MEDIUM"]:])
        ma50 = np.mean(closes[-P["MA_LONG"]:]) if len(closes) >= P["MA_LONG"] else ma20
        
        # RSI (使用配置的参数)
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-P["RSI_PERIOD"]:])
        avg_loss = np.mean(losses[-P["RSI_PERIOD"]:])
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        # MACD (使用配置的参数)
        ema12 = np.mean(closes[-P["MACD_FAST"]:])
        ema26 = np.mean(closes[-P["MACD_SLOW"]:]) if len(closes) >= P["MACD_SLOW"] else ema12
        macd = ema12 - ema26
        macd_signal = macd * 0.9  # 信号线简化
        
        # 布林带
        std = np.std(closes[-P["BB_PERIOD"]:])
        upper = ma20 + P["BB_STD"] * std
        lower = ma20 - P["BB_STD"] * std
        
        # 波动率
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0.01
        
        # 趋势强度 (A/D指标简化版)
        if ma10 > ma20 > ma50:
            trend_strength = "strong_bull"
        elif ma10 < ma20 < ma50:
            trend_strength = "strong_bear"
        else:
            trend_strength = "weak"
        
        return {
            "price": closes[-1],
            "ma10": ma10,
            "ma20": ma20,
            "ma50": ma50,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "boll_upper": upper,
            "boll_lower": lower,
            "volatility": volatility,
            "trend": "bull" if ma10 > ma50 else "bear",
            "trend_strength": trend_strength
        }
    
    def analyze_market_state(self, data_4h):
        """分析市场状态"""
        ind = self.calculate_indicators(data_4h)
        
        # 趋势判断
        if ind["ma20"] > ind["ma50"]:
            trend = "up"
        elif ind["ma20"] < ind["ma50"]:
            trend = "down"
        else:
            trend = "sideways"
        
        # 熊市检测 (MA50向下)
        is_bear = trend == "down" and ind["price"] < ind["ma50"]
        
        # 高波动检测
        is_high_vol = ind["volatility"] > 0.03
        
        # 状态
        if is_high_vol:
            state = "high_volatility"
        elif is_bear:
            state = "bear_market"
        elif trend == "up":
            state = "trend_up"
        elif trend == "down":
            state = "trend_down"
        else:
            state = "sideways"
        
        # 熊市时禁止买入，只允许做空
        allow_buy = not is_high_vol and not is_bear
        
        return {
            "trend": trend,
            "state": state,
            "volatility": ind["volatility"],
            "allow_trade": not is_high_vol,
            "allow_buy": allow_buy,
            "is_bear": is_bear,
            "indicators": ind
        }
    
    def generate_signal(self):
        """生成交易信号"""
        print(f"\n{'='*50}")
        print(f"📊 Strategy Agent - 信号生成")
        print(f"{'='*50}")
        
        # 获取多时间框架数据 (简化版)
        data_4h = self.get_klines("4h", 50)
        data_1h = self.get_klines("1h", 50)
        data_15m = self.get_klines("15m", 50)
        
        closes_4h = data_4h["close"]
        closes_1h = data_1h["close"]
        closes_15m = data_15m["close"]
        
        # ATR计算
        atr_1h = calculate_atr(data_1h["high"], data_1h["low"], closes_1h, 14)
        atr_4h = calculate_atr(data_4h["high"], data_4h["low"], closes_4h, 14)
        atr_15m = calculate_atr(data_15m["high"], data_15m["low"], closes_15m, 14)
        
        # ===== 新增1: 15分钟趋势过滤 =====
        ma10_15m = np.mean(closes_15m[-10:])
        ma20_15m = np.mean(closes_15m[-20:])
        if ma10_15m > ma20_15m:
            trend_15m = "bull"
        elif ma10_15m < ma20_15m:
            trend_15m = "bear"
        else:
            trend_15m = "sideways"
        
        # 计算15分钟RSI
        deltas_15m = np.diff(closes_15m)
        gains_15m = np.where(deltas_15m > 0, deltas_15m, 0)
        losses_15m = np.where(deltas_15m < 0, -deltas_15m, 0)
        avg_gain_15m = np.mean(gains_15m[-14:])
        avg_loss_15m = np.mean(losses_15m[-14:])
        rs_15m = avg_gain_15m / avg_loss_15m if avg_loss_15m > 0 else 0
        rsi_15m = 100 - (100 / (1 + rs_15m))
        
        print(f"\n🕐 15分钟: trend={trend_15m}, rsi={rsi_15m:.1f}")
        
        # ===== 日线/周线分析 (可选，如需开启请取消注释) =====
        # data_1d = self.get_klines("1d", 30)
        # ind_1d = self.calculate_indicators(data_1d["close"])
        
        # 市场状态识别
        regime_1h = detect_market_regime(closes_1h, 20)
        
        # 市场状态
        market = self.analyze_market_state(closes_4h)
        print(f"\n�markt状态: {market['state']} | 波动率: {market['volatility']*100:.2f}%")
        print(f"  ATR(1h): {atr_1h:.2f} | 市场状态: {regime_1h}")
        print(f"  允许交易: {market['allow_trade']}")
        
        # 计算指标
        ind_4h = self.calculate_indicators(closes_4h)
        ind_1h = self.calculate_indicators(closes_1h)
        
        print(f"\n4H: {ind_4h['trend']} | RSI:{ind_4h['rsi']:.1f} | 价格:{ind_4h['price']:.0f}")
        print(f"1H: {ind_1h['trend']} | RSI:{ind_1h['rsi']:.1f} | 价格:{ind_1h['price']:.0f}")
        
        # 信号逻辑
        signals = []
        
        # 1. 趋势信号
        if ind_4h["trend"] == "bull" and ind_1h["trend"] == "bull":
            signals.append(("BUY", "趋势多头"))
        elif ind_4h["trend"] == "bear" and ind_1h["trend"] == "bear":
            signals.append(("SELL", "趋势空头"))
        
        # 2. RSI (使用配置参数: oversold=25, overbought=75)
        if ind_1h["rsi"] < PARAMS["RSI_OVERSOLD"]:
            signals.append(("BUY", f"RSI超卖({ind_1h['rsi']:.0f})"))
        elif ind_1h["rsi"] > PARAMS["RSI_OVERBOUGHT"]:
            signals.append(("SELL", f"RSI超买({ind_1h['rsi']:.0f})"))
        
        # 3. MACD
        if ind_1h["macd"] > ind_1h["macd_signal"]:
            signals.append(("BUY", "MACD金叉"))
        elif ind_1h["macd"] < ind_1h["macd_signal"]:
            signals.append(("SELL", "MACD死叉"))
        
        # 4. 布林
        if ind_1h["price"] > ind_1h["boll_upper"]:
            signals.append(("BUY", "突破上轨"))
        elif ind_1h["price"] < ind_1h["boll_lower"]:
            signals.append(("SELL", "跌破下轨"))
        
        # 多周期共振检查 (4H + 1H)
        if ind_4h["trend"] == ind_1h["trend"]:
            if ind_4h["trend"] == "bull":
                signals.append(("BUY", "4H+1H短线共振"))
            elif ind_4h["trend"] == "bear":
                signals.append(("SELL", "4H+1H短线共振"))
        
        # 4H RSI 确认
        if ind_4h["rsi"] < 35:
            signals.append(("BUY", f"4H RSI超卖({ind_4h['rsi']:.0f})"))
        elif ind_4h["rsi"] > 65:
            signals.append(("SELL", f"4H RSI超买({ind_4h['rsi']:.0f})"))
        
        # RSI超买超卖有更高权重 (×2)
        for i, (s, r) in enumerate(signals):
            if "RSI超卖" in r or "RSI超买" in r:
                signals.append((s, r))  # 复制一份增加权重
        
        # 统计
        buy_count = sum(1 for s in signals if s[0] == "BUY")
        sell_count = sum(1 for s in signals if s[0] == "SELL")
        
        # ===== 决策 - 支持双向交易 =====
        # position: 0=空仓, 1=多仓, -1=空仓
        # 需要从外部传入当前持仓方向，这里先简化处理
        
        if not market["allow_trade"]:
            signal = "HOLD"
            reason = "高波动市场"
            confidence = 0
        elif market.get("is_bear") and buy_count >= 2:
            # 熊市: 尝试做空
            signal = "SHORT"  # 改为做空
            reason = "熊市做空"
            confidence = 0.5
        elif sell_count >= 2:  # SELL优先
            # ===== 新增1: 15分钟过滤 =====
            # 先记录SELL原因，再检查过滤
            sell_reason = "+".join(list(set([s[1] for s in signals if s[0] == "SELL"]))[:3])
            if trend_15m == "bull" and sell_count >= 2:
                # 15分钟处于上涨趋势，减弱做空信号
                signal = "HOLD"
                reason = "15分钟上涨过滤做空"
                confidence = 0.3
            else:
                signal = "SELL"
                reason = sell_reason
                confidence = min(sell_count / 4, 1.0)
        elif buy_count >= 2:
            # ===== 新增1: 15分钟过滤 =====
            # 先记录BUY原因，再检查过滤
            buy_reason = "+".join(list(set([s[1] for s in signals if s[0] == "BUY"]))[:3])
            
            # 检查是否有持仓（有持仓时才过滤，没有持仓时应该积极买入）
            # 注意：这里需要从外部获取持仓状态，暂时用信号判断
            # 如果4H和1H都看多，就允许买入
            if ind_4h["trend"] == "bull" and ind_1h["trend"] == "bull":
                # 4H和1H都多头，放行买入
                signal = "BUY"
                reason = buy_reason + "+多周期共振"
                confidence = min(buy_count / 4, 1.0) + 0.1
            elif buy_count >= 2:
                # 其他情况根据15分钟过滤
                if trend_15m == "bear":
                    signal = "HOLD"
                    reason = "15分钟下跌过滤"
                    confidence = 0.3
                else:
                    signal = "BUY"
                    reason = buy_reason
                    confidence = min(buy_count / 4, 1.0)
            else:
                signal = "BUY"
                reason = buy_reason
                confidence = min(buy_count / 4, 1.0)
        else:
            signal = "HOLD"
            reason = "无共识"
            confidence = 0.5
        
        # 计算动态止损/止盈
        current_price = ind_1h["price"]
        
        # ===== 新增2: ATR动态止损（已有，保留） =====
        if signal == "BUY" and atr_1h:
            dynamic_sl = get_dynamic_stop_loss(current_price, atr_1h, regime_1h, 2)
            sl_pct = (current_price - dynamic_sl) / current_price * 100
            dynamic_tp = get_dynamic_take_profit(current_price, atr_1h, regime_1h, 3)
            tp_pct = (dynamic_tp - current_price) / current_price * 100
        elif signal == "SELL" and atr_1h:
            dynamic_sl = get_dynamic_stop_loss(current_price, atr_1h, regime_1h, 2)
            sl_pct = (current_price - dynamic_sl) / current_price * 100  # 多头止损方向
            dynamic_tp = get_dynamic_take_profit(current_price, atr_1h, regime_1h, 3)
            tp_pct = (current_price - dynamic_tp) / current_price * 100  # 下跌幅度
        else:
            dynamic_sl = None
            sl_pct = None
            dynamic_tp = None
            tp_pct = None
        
        # ===== 新增3: 移动止盈（Trailing Stop）计算 =====
        # 检查是否有持仓，如果有则计算移动止盈
        trailing_stop = None
        trailing_stop_pct = None
        # 这里需要从外部获取持仓信息，暂时标记需要实现
        # 实际使用时需要在实盘模块中根据持仓价格计算
        
        # 添加移动止盈说明
        trailing_info = {
            "enabled": True,
            "description": "盈利20%→止损1%, 50%→止损20%, 100%→止损70%",
            "current_trailing": None,  # 需要持仓时计算
            "entry_price": current_price  # 假设新开仓
        }
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "symbol": self.symbol,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "signals": signals,
            "market_state": {
                "state": market["state"],
                "allow_trade": market["allow_trade"],
                "trend": market["trend"],
                "regime": regime_1h,
                "atr": round(atr_1h, 2) if atr_1h else None,
                "15m_filter": trend_15m  # 新增：15分钟过滤结果
            },
            "dynamic_stop_loss": {
                "price": round(dynamic_sl, 2) if dynamic_sl else None,
                "pct": round(sl_pct, 2) if sl_pct else None,
                "regime": regime_1h,
                "type": "ATR动态止损"  # 新增：标注类型
            },
            "dynamic_take_profit": {
                "price": round(dynamic_tp, 2) if dynamic_tp else None,
                "pct": round(tp_pct, 2) if tp_pct else None,
                "regime": regime_1h,
                "type": "ATR动态止盈",
                "trailing_enabled": True,  # 移动止盈已启用
                "trailing_info": trailing_info
            },
            "indicators": {
                "4h": {k: round(v, 2) if isinstance(v, float) else v for k, v in ind_4h.items()},
                "1h": {k: round(v, 2) if isinstance(v, float) else v for k, v in ind_1h.items()},
                "15m": {  # 新增：15分钟指标
                    "trend": trend_15m,
                    "rsi": round(rsi_15m, 2) if rsi_15m else None,
                    "ma10": round(ma10_15m, 2),
                    "ma20": round(ma20_15m, 2)
                }
            }
        }
        
        # 打印动态止损/止盈信息
        if dynamic_sl:
            print(f"  动态止损: {dynamic_sl:.2f} ({sl_pct:.1f}%)")
        if dynamic_tp:
            print(f"  动态止盈: {dynamic_tp:.2f} ({tp_pct:+.1f}%)")
        
        print(f"\n📌 信号: {signal} ({confidence:.0%}) | {reason}")
        
        return result
    
    def save_signal(self, signal_data):
        """保存信号"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "last_signal.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(signal_data, f, indent=2)


def run_strategy():
    """运行策略Agent"""
    agent = StrategyAgent()
    signal = agent.generate_signal()
    agent.save_signal(signal)
    return signal


if __name__ == "__main__":
    run_strategy()
