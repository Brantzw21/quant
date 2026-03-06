#!/usr/bin/env python3
"""
增强版策略信号生成
整合 ADX 趋势强度 + ATR 动态止损 + 成交量确认
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

from binance.client import Client
from config import API_KEY, SECRET_KEY, TESTNET, REAL_API_KEY, REAL_SECRET_KEY
import numpy as np
import pandas as pd
import ta
import json
from datetime import datetime

# ===== 策略参数 =====
MA_FAST = 10
MA_MID = 20
MA_SLOW = 50

RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14

ADX_THRESHOLD = 20      # 趋势强度阈值
VOLUME_MULTIPLIER = 1.5  # 成交量倍数
RSI_OVERSOLD = 40       # RSI 超卖阈值
RSI_OVERBOUGHT = 60     # RSI 超买阈值

# 使用实盘API获取数据（从config读取）
DATA_API_KEY = REAL_API_KEY
DATA_SECRET_KEY = REAL_SECRET_KEY

def get_klines_full(symbol, interval, limit=100):
    """获取完整K线数据（包含 high, low, volume）"""
    # 使用实盘获取数据（测试网K线数据有bug）
    client = Client(DATA_API_KEY, DATA_SECRET_KEY, testnet=False)
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    df = pd.DataFrame(klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    return df

def get_multi_timeframe():
    """获取多周期数据"""
    client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)
    
    intervals = {
        '4h': 50,
        '1h': 50,
        '1d': 30,
        '1w': 20
    }
    
    data = {}
    for iv, lim in intervals.items():
        try:
            data[iv] = get_klines_full('BTCUSDT', iv, lim)
        except Exception as e:
            print(f"获取 {iv} 数据失败: {e}")
            data[iv] = pd.DataFrame()
    
    return data

def calculate_indicators(df):
    """计算技术指标"""
    if len(df) < 50:
        return None
    
    # MA
    df['ma10'] = df['close'].rolling(MA_FAST).mean()
    df['ma20'] = df['close'].rolling(MA_MID).mean()
    df['ma50'] = df['close'].rolling(MA_SLOW).mean()
    
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], RSI_PERIOD).rsi()
    
    # ADX (趋势强度)
    df['adx'] = ta.trend.ADXIndicator(
        df['high'], df['low'], df['close'], ADX_PERIOD
    ).adx()
    
    # ATR (动态止损)
    df['atr'] = ta.volatility.AverageTrueRange(
        df['high'], df['low'], df['close'], ATR_PERIOD
    ).average_true_range()
    
    # 成交量均线
    df['vol_ma'] = df['volume'].rolling(20).mean()
    
    return df

def analyze_trend(df):
    """分析趋势"""
    last = df.iloc[-1]
    
    # 趋势判断
    trend_up = bool(last['ma10'] > last['ma20'] > last['ma50'])
    trend_down = bool(last['ma10'] < last['ma20'] < last['ma50'])
    
    # 成交量确认
    volume_ok = bool(last['volume'] > last['vol_ma'] * VOLUME_MULTIPLIER)
    
    # 趋势强度
    trend_strong = bool(last['adx'] > ADX_THRESHOLD)
    
    return {
        'trend': 'bull' if trend_up else ('bear' if trend_down else 'side'),
        'trend_up': trend_up,
        'trend_down': trend_down,
        'volume_ok': volume_ok,
        'trend_strong': trend_strong,
        'adx': float(last['adx']),
        'atr': float(last['atr']),
        'rsi': float(last['rsi']),
        'price': float(last['close']),
        'ma10': float(last['ma10']),
        'ma20': float(last['ma20']),
        'ma50': float(last['ma50']),
    }

def generate_signal():
    print("=" * 50)
    print("获取多周期数据...")
    
    # 获取多周期数据
    data = get_multi_timeframe()
    
    # 计算各周期指标
    indicators = {}
    for tf in ['1w', '1d', '4h', '1h']:
        if tf in data and len(data[tf]) > 0:
            df_with_indicators = calculate_indicators(data[tf].copy())
            if df_with_indicators is not None:
                indicators[tf] = analyze_trend(df_with_indicators)
                indicators[tf]['df'] = df_with_indicators
    
    if not indicators:
        print("数据不足")
        return None
    
    # 打印各周期状态
    print("\n📊 各周期状态:")
    for tf in ['1w', '1d', '4h', '1h']:
        if tf in indicators:
            ind = indicators[tf]
            print(f"  {tf}: 趋势={ind['trend']:4s} | RSI={ind['rsi']:5.1f} | ADX={ind['adx']:5.1f} | 量OK={ind['volume_ok']}")
    
    # ===== 多周期趋势评分 =====
    trend_score = 0
    if indicators.get('1w', {}).get('trend') == 'bull': trend_score += 3
    if indicators.get('1d', {}).get('trend') == 'bull': trend_score += 2
    if indicators.get('4h', {}).get('trend') == 'bull': trend_score += 1
    if indicators.get('1w', {}).get('trend') == 'bear': trend_score -= 3
    if indicators.get('1d', {}).get('trend') == 'bear': trend_score -= 2
    if indicators.get('4h', {}).get('trend') == 'bear': trend_score -= 1
    
    # ===== 信号生成 =====
    signal = "HOLD"
    confidence = 0.5
    reason = "观望"
    stop_loss = None
    take_profit = None
    
    # 主要参考 4h 周期
    ind_4h = indicators.get('4h', {})
    ind_1h = indicators.get('1h', {})
    ind_1d = indicators.get('1d', {})
    
    price = ind_4h.get('price', 0)
    atr = ind_4h.get('atr', 0)
    
    # 转为 Python bool
    trend_up = bool(ind_4h.get('trend_up', False))
    trend_down = bool(ind_4h.get('trend_down', False))
    trend_strong = bool(ind_4h.get('trend_strong', False))
    volume_ok = bool(ind_4h.get('volume_ok', False))
    rsi_val = float(ind_4h.get('rsi', 50))
    
    # 买入条件: 上涨趋势 + ADX强 + 成交量OK + RSI超卖
    buy_conditions = (
        trend_up and 
        trend_strong and 
        volume_ok and 
        rsi_val < RSI_OVERSOLD
    )
    
    # 卖出条件: 下跌趋势 + ADX强 + 成交量OK + RSI超买
    sell_conditions = (
        trend_down and 
        trend_strong and 
        volume_ok and 
        rsi_val > RSI_OVERBOUGHT
    )
    
    # 多周期共振买入 (周线+日线+4h 同时看多)
    multi_buy = (
        indicators.get('1w', {}).get('trend') == 'bull' and
        indicators.get('1d', {}).get('trend') == 'bull' and
        indicators.get('4h', {}).get('trend') == 'bull' and
        trend_strong
    )
    
    # 多周期共振卖出
    multi_sell = (
        indicators.get('1w', {}).get('trend') == 'bear' and
        indicators.get('1d', {}).get('trend') == 'bear' and
        indicators.get('4h', {}).get('trend') == 'bear' and
        trend_strong
    )
    
    if multi_buy or buy_conditions:
        signal = "BUY"
        confidence = 0.8 if multi_buy else 0.65
        reason = "多周期共振" if multi_buy else "趋势+ADX+RSI超卖"
        
        # ATR 动态止损
        if atr > 0:
            stop_loss = round(price - 1.5 * atr, 2)
            take_profit = round(price + 3 * atr, 2)
        
    elif multi_sell or sell_conditions:
        signal = "SELL"
        confidence = 0.8 if multi_sell else 0.65
        reason = "多周期共振" if multi_sell else "趋势+ADX+RSI超买"
        
        # ATR 动态止损 (空头)
        if atr > 0:
            stop_loss = round(price + 1.5 * atr, 2)
            take_profit = round(price - 3 * atr, 2)
    
    else:
        # 弱信号 (只有部分条件满足)
        if trend_score >= 3 and rsi_val < 45:
            signal = "BUY"
            confidence = 0.55
            reason = "趋势偏多+RSI低位"
        elif trend_score <= -3 and rsi_val > 55:
            signal = "SELL"
            confidence = 0.55
            reason = "趋势偏空+RSI高位"
        else:
            signal = "HOLD"
            confidence = 0.5
            # 原因分析
            if not trend_strong:
                reason = "ADX不足(趋势不强)"
            elif not volume_ok:
                reason = "成交量不足"
            elif abs(trend_score) < 3:
                reason = "多周期分歧"
            else:
                reason = "条件不满足"
    
    # 构建结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "BTCUSDT",
        "signal": signal,
        "confidence": confidence,
        "reason": reason,
        "trend_score": trend_score,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "indicators": {
            "1w": {
                "trend": indicators.get('1w', {}).get('trend', 'N/A'),
                "rsi": round(indicators.get('1w', {}).get('rsi', 0), 1),
                "adx": round(indicators.get('1w', {}).get('adx', 0), 1)
            },
            "1d": {
                "trend": indicators.get('1d', {}).get('trend', 'N/A'),
                "rsi": round(indicators.get('1d', {}).get('rsi', 0), 1),
                "adx": round(indicators.get('1d', {}).get('adx', 0), 1)
            },
            "4h": {
                "price": round(indicators.get('4h', {}).get('price', 0), 2),
                "rsi": round(indicators.get('4h', {}).get('rsi', 0), 1),
                "adx": round(indicators.get('4h', {}).get('adx', 0), 1),
                "atr": round(indicators.get('4h', {}).get('atr', 0), 2),
                "trend": indicators.get('4h', {}).get('trend', 'N/A'),
                "volume_ok": indicators.get('4h', {}).get('volume_ok', False)
            },
            "1h": {
                "price": round(indicators.get('1h', {}).get('price', 0), 2),
                "rsi": round(indicators.get('1h', {}).get('rsi', 0), 1),
                "adx": round(indicators.get('1h', {}).get('adx', 0), 1),
                "trend": indicators.get('1h', {}).get('trend', 'N/A')
            }
        }
    }
    
    # 保存
    os.makedirs('/root/.openclaw/workspace/quant/quant/data', exist_ok=True)
    with open('/root/.openclaw/workspace/quant/quant/data/last_signal.json', 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*50}")
    print(f"📈 信号: {signal} | 置信度: {confidence:.0%}")
    print(f"📝 原因: {reason}")
    print(f"💰 价格: {price:.2f} | ATR: {atr:.2f}")
    if stop_loss and take_profit:
        print(f"🛡️ 止损: {stop_loss} | 🎯 止盈: {take_profit}")
    print(f"{'='*50}")
    
    return result

if __name__ == "__main__":
    generate_signal()
