#!/usr/bin/env python3
"""
A股模拟盘自动交易
根据多标的信号自动执行买卖
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astock_simulator import AStockSimulator
from astock_multi import AStockMultiStrategy
from astock_config import A_STOCK_INDEXES
from notify import send_message
from datetime import datetime

def auto_trade():
    """自动交易"""
    print("=== A股模拟盘自动交易 ===")
    
    # 1. 获取最新信号
    strategy = AStockMultiStrategy()
    results = strategy.run(A_STOCK_INDEXES)
    
    if not results:
        print("无信号")
        return
    
    # 2. 初始化模拟账户
    sim = AStockSimulator()
    account = sim.get_status()
    
    print(f"\n账户状态: 现金 ¥{account['cash']:,.0f}, 总资产 ¥{account['total_value']:,.0f}")
    
    # 3. 获取当前持仓
    current_positions = {p['code'] for p in account['positions']}
    print(f"当前持仓: {current_positions}")
    
    # 4. 处理信号
    buy_signals = [r for r in results if r['signal'] == 'BUY' and r['code'] not in current_positions]
    sell_signals = [r for r in results if r['signal'] == 'SELL' and r['code'] in current_positions]
    
    print(f"\n买入信号: {len(buy_signals)}个")
    print(f"卖出信号: {len(sell_signals)}个")
    
    # 5. 执行买入 (每次用20%仓位)
    for signal in buy_signals:
        code = signal['code']
        name = signal['name']
        confidence = signal['confidence']
        
        # 计算买入金额 (仓位的20%)
        amount = account['cash'] * 0.2
        
        if amount < 10000:
            print(f"  资金不足，跳过买入 {name}")
            continue
        
        result = sim.buy(code, name, amount=amount)
        if result['success']:
            print(f"  ✅ 买入 {name}: {result['message']}")
        else:
            print(f"  ❌ 买入失败 {name}: {result['message']}")
    
    # 6. 执行卖出
    for signal in sell_signals:
        code = signal['code']
        
        result = sim.sell(code, all=True)
        if result['success']:
            print(f"  ✅ 卖出: {result['message']}")
        else:
            print(f"  ❌ 卖出失败: {result['message']}")
    
    # 7. 更新账户状态
    account = sim.get_status()
    
    # 8. 发送通知
    msg = f"""
📈 A股模拟盘自动交易 - {datetime.now().strftime('%Y-%m-%d %H:%M')}

【账户状态】
现金: ¥{account['cash']:,.0f}
持仓市值: ¥{account['total_value'] - account['cash']:,.0f}
总资产: ¥{account['total_value']:,.0f}
总盈亏: ¥{account['total_pnl']:,.0f} ({account['total_pnl_pct']:+.2f}%)

【交易动作】
买入: {len(buy_signals)}个
卖出: {len(sell_signals)}个

【当前持仓】
"""
    
    for p in account['positions']:
        msg += f"{p['name']}: {p['quantity']}股 (¥{p['pnl']:+,.0f})\n"
    
    send_message(msg)
    
    print(f"\n✅ 自动交易完成")
    print(f"总盈亏: ¥{account['total_pnl']:,.0f}")


def main():
    auto_trade()


if __name__ == "__main__":
    main()
