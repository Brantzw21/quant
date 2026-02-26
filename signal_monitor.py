"""
手动跟单系统 - 信号输出
每天运行，自动检测信号，推送到文件/终端
"""
import json
from datetime import datetime
from autoquant.core.data_service import get_data_service
from strategies import get_strategy


def generate_signals():
    """生成当日信号"""
    params = {"rsi_period": 9, "ma_period": 60, "hold_days": 5, "oversold": 25, "exit_threshold": 70}
    info = get_strategy("robust_rsi")
    
    ds = get_data_service()
    data = ds.get_stock_data("sh.000300", "2024-01-01", "2025-02-25").to_dict('records')
    
    if len(data) < 70:
        return {"error": "数据不足"}
    
    latest = data[-1]
    date = latest["date"]
    price = float(latest["close"])
    
    closes = [float(d["close"]) for d in data]
    ma60 = sum(closes[-60:]) / 60
    
    rsi_period = 9
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-rsi_period:]) / rsi_period
    avg_loss = sum(losses[-rsi_period:]) / rsi_period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    trend = "UP" if price > ma60 else "DOWN"
    
    result = info["signal_func"](data, params)
    if isinstance(result, tuple):
        signal, size = result
    else:
        signal = result
        size = 1.0
    
    return {
        "date": date,
        "price": price,
        "rsi": rsi,
        "ma60": ma60,
        "trend": trend,
        "signal": signal,
        "position_size": size,
        "action": get_action(signal, rsi, trend)
    }


def get_action(signal, rsi, trend):
    """获取操作建议"""
    if signal == "BUY":
        return "买入"
    elif signal == "SELL":
        return "卖出"
    else:
        return "持有/观望"


def main():
    print("="*60)
    print("手动跟单信号")
    print("="*60)
    
    result = generate_signals()
    
    print(f"\n日期: {result['date']}")
    print(f"价格: {result['price']:.2f}")
    print(f"RSI: {result['rsi']:.1f}")
    print(f"MA60: {result['ma60']:.2f}")
    print(f"趋势: {result['trend']}")
    print(f"信号: {result['signal']}")
    print(f"操作: {result['action']}")
    
    signal_file = "logs/latest_signal.json"
    with open(signal_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n信号已保存: {signal_file}")
    
    print("\n" + "="*60)
    print("手动操作步骤:")
    print("="*60)
    print("1. 打开东方财富APP/PC客户端")
    print("2. 搜索510300 (沪深300ETF)")
    print(f"3. {'买入' if result['signal']=='BUY' else '卖出' if result['signal']=='SELL' else '观望'}")
    print(f"4. 价格: 参考 {result['price']:.2f}")
    print("5. 数量: 100的整数倍")
    print("="*60)


if __name__ == "__main__":
    main()
