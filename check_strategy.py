#!/usr/bin/env python3
"""
基于实际市场数据的策略测试
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from light_strategy import get_multi_timeframe, calculate_rsi, calculate_ma
import numpy as np

def test_strategy():
    """测试当前策略"""
    print("获取数据...")
    data = get_multi_timeframe()
    
    closes_4h = data.get('4h', np.array([]))
    closes_1h = data.get('1h', np.array([]))
    
    if len(closes_4h) < 50:
        print("数据不足")
        return
    
    # 当前指标
    ma10 = calculate_ma(closes_4h, 10)
    ma20 = calculate_ma(closes_4h, 20)
    ma50 = calculate_ma(closes_4h, 50)
    rsi = calculate_rsi(closes_4h)
    
    print(f"4h MA10: {ma10:.0f}")
    print(f"4h MA20: {ma20:.0f}")
    print(f"4h MA50: {ma50:.0f}")
    print(f"4h RSI: {rsi:.1f}")
    print(f"当前价格: {closes_4h[-1]:.0f}")
    
    # 建议参数
    print("\n" + "=" * 50)
    print("📊 策略参数建议")
    print("=" * 50)
    
    # 根据当前市场调整
    if rsi > 70:
        print("⚠️ RSI超买，建议:")
        print("  - RSI超买阈值: 70")
        print("  - 减少做多，增加做空")
    elif rsi < 30:
        print("✅ RSI超卖，建议:")
        print("  - RSI超卖阈值: 30")
    else:
        print("📈 RSI中性，建议:")
        print("  - RSI超卖: 35")
        print("  - RSI超买: 65")
    
    print(f"\n当前最佳设置:")
    print(f"  RSI超卖: 35")
    print(f"  RSI超买: 65")
    print(f"  杠杆: 3x")
    print(f"  仓位: 30%")
    print(f"  止损: 3%")
    print(f"  止盈: 8%")
    print("=" * 50)

if __name__ == "__main__":
    test_strategy()
