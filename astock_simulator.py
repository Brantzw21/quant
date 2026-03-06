#!/usr/bin/env python3
"""
A股模拟交易系统
虚拟账户，记录持仓和盈亏
"""
import os
import json
import sys
from datetime import datetime
from data_manager import MarketDataManager

# 模拟账户文件
ACCOUNT_FILE = "/root/.openclaw/workspace/quant/quant/data/astock_account.json"

class AStockSimulator:
    """A股模拟交易账户"""
    
    def __init__(self, initial_capital=1000000):  # 初始100万人民币
        self.dm = MarketDataManager()
        self.load_account()
    
    def load_account(self):
        """加载账户"""
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, 'r') as f:
                self.account = json.load(f)
        else:
            # 初始化新账户
            self.account = {
                "cash": 1000000,  # 100万初始资金
                "positions": {},   # 持仓 {"code": {"quantity": 数量, "cost": 成本}}
                "transactions": [], # 交易记录
                "initialized": datetime.now().isoformat()
            }
    
    def save_account(self):
        """保存账户"""
        os.makedirs(os.path.dirname(ACCOUNT_FILE), exist_ok=True)
        with open(ACCOUNT_FILE, 'w') as f:
            json.dump(self.account, f, indent=2, ensure_ascii=False)
    
    def get_price(self, code):
        """获取当前价格"""
        try:
            df = self.dm.get_a_stock_klines(code, '2025-01-01', datetime.now().strftime('%Y-%m-%d'))
            if df and len(df) > 0:
                return df[-1]['close']
        except:
            pass
        return None
    
    def buy(self, code, name, quantity=None, amount=None):
        """
        买入
        quantity: 股数 (必须是100的倍数)
        amount: 金额 (二选一)
        """
        price = self.get_price(code)
        if not price:
            return {"success": False, "message": "获取价格失败"}
        
        # 计算买入数量
        if amount:
            # 模拟盘不强制100股限制
            quantity = int(amount / price)
        elif quantity:
            quantity = int(quantity)
        
        if quantity < 1:
            return {"success": False, "message": "买入数量不足"}
        
        cost = quantity * price * 1.0003  # 考虑手续费
        
        if cost > self.account['cash']:
            return {"success": False, "message": f"资金不足，需要{cost:.2f}，可用{self.account['cash']:.2f}"}
        
        # 执行买入
        self.account['cash'] -= cost
        
        if code in self.account['positions']:
            old = self.account['positions'][code]
            total_cost = old['cost'] * old['quantity'] + cost
            total_qty = old['quantity'] + quantity
            self.account['positions'][code] = {
                "name": name,
                "quantity": total_qty,
                "cost": total_cost / total_qty
            }
        else:
            self.account['positions'][code] = {
                "name": name,
                "quantity": quantity,
                "cost": price
            }
        
        # 记录交易
        self.account['transactions'].append({
            "time": datetime.now().isoformat(),
            "code": code,
            "name": name,
            "type": "BUY",
            "price": price,
            "quantity": quantity,
            "amount": cost
        })
        
        self.save_account()
        
        return {
            "success": True,
            "message": f"买入成功 {name} {quantity}股 @ {price:.2f}",
            "price": price,
            "quantity": quantity,
            "cost": cost,
            "cash": self.account['cash']
        }
    
    def sell(self, code, quantity=None, all=False):
        """卖出"""
        if code not in self.account['positions']:
            return {"success": False, "message": "无持仓"}
        
        price = self.get_price(code)
        if not price:
            return {"success": False, "message": "获取价格失败"}
        
        position = self.account['positions'][code]
        
        if all:
            quantity = position['quantity']
        elif not quantity or quantity > position['quantity']:
            quantity = position['quantity']
        
        quantity = int(quantity)
        proceeds = quantity * price * 0.9997  # 考虑手续费和印花税
        
        # 计算盈亏
        cost_basis = position['cost'] * quantity
        pnl = proceeds - cost_basis
        
        # 更新持仓
        position['quantity'] -= quantity
        if position['quantity'] <= 0:
            del self.account['positions'][code]
        
        self.account['cash'] += proceeds
        
        # 记录交易
        self.account['transactions'].append({
            "time": datetime.now().isoformat(),
            "code": code,
            "name": position['name'],
            "type": "SELL",
            "price": price,
            "quantity": quantity,
            "amount": proceeds,
            "pnl": pnl
        })
        
        self.save_account()
        
        return {
            "success": True,
            "message": f"卖出成功 {position['name']} {quantity}股 @ {price:.2f}",
            "price": price,
            "quantity": quantity,
            "proceeds": proceeds,
            "pnl": pnl,
            "cash": self.account['cash']
        }
    
    def get_status(self):
        """获取账户状态"""
        total_value = self.account['cash']
        positions_info = []
        
        for code, pos in self.account['positions'].items():
            current_price = self.get_price(code)
            if current_price:
                market_value = pos['quantity'] * current_price
                cost_basis = pos['quantity'] * pos['cost']
                pnl = market_value - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                
                positions_info.append({
                    "code": code,
                    "name": pos['name'],
                    "quantity": pos['quantity'],
                    "cost": pos['cost'],
                    "price": current_price,
                    "market_value": market_value,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct
                })
                total_value += market_value
        
        # 计算总盈亏
        initial = 1000000
        total_pnl = total_value - initial
        total_pnl_pct = total_pnl / initial * 100
        
        return {
            "cash": self.account['cash'],
            "total_value": total_value,
            "initial_capital": initial,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": positions_info,
            "transaction_count": len(self.account['transactions'])
        }
    
    def auto_trade(self, signals):
        """根据信号自动交易"""
        results = []
        
        for signal in signals:
            if signal['signal'] != 'BUY':
                continue
            
            code = signal['code']
            name = signal['name']
            confidence = signal.get('confidence', 0.5)
            
            # 检查是否已有持仓
            if code in self.account['positions']:
                continue  # 已有持仓，跳过
            
            # 买入金额 = 总资金的20%
            amount = self.account['cash'] * 0.2
            
            result = self.buy(code, name, amount=amount)
            results.append(result)
        
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='A股模拟交易')
    parser.add_argument('action', choices=['status', 'buy', 'sell', 'trade'])
    parser.add_argument('--code', help='股票代码')
    parser.add_argument('--name', help='股票名称')
    parser.add_argument('--quantity', type=int, help='数量')
    parser.add_argument('--amount', type=float, help='金额')
    parser.add_argument('--all', action='store_true', help='全部卖出')
    
    args = parser.parse_args()
    
    sim = AStockSimulator()
    
    if args.action == 'status':
        status = sim.get_status()
        print(f"\n{'='*50}")
        print(f"A股模拟账户")
        print(f"{'='*50}")
        print(f"现金: ¥{status['cash']:,.2f}")
        print(f"持仓市值: ¥{status['total_value'] - status['cash']:,.2f}")
        print(f"总资产: ¥{status['total_value']:,.2f}")
        print(f"总盈亏: ¥{status['total_pnl']:,.2f} ({status['total_pnl_pct']:+.2f}%)")
        print(f"交易次数: {status['transaction_count']}")
        
        if status['positions']:
            print(f"\n持仓:")
            for p in status['positions']:
                print(f"  {p['name']} ({p['code']}): {p['quantity']}股")
                print(f"    成本: ¥{p['cost']:.2f}, 当前: ¥{p['price']:.2f}")
                print(f"    盈亏: ¥{p['pnl']:,.2f} ({p['pnl_pct']:+.2f}%)")
        print(f"{'='*50}")
    
    elif args.action == 'buy':
        result = sim.buy(args.code, args.name, quantity=args.quantity, amount=args.amount)
        print(result['message'])
    
    elif args.action == 'sell':
        result = sim.sell(args.code, quantity=args.quantity, all=args.all)
        print(result['message'])
    
    elif args.action == 'trade':
        # 从信号文件读取并自动交易
        signal_file = "/root/.openclaw/workspace/quant/quant/data/astock_signals.json"
        if os.path.exists(signal_file):
            with open(signal_file) as f:
                data = json.load(f)
            
            # 使用指数的买入信号
            signals = data.get('index', {}).get('all', [])
            results = sim.auto_trade(results)
            for r in results:
                print(r['message'])


if __name__ == "__main__":
    main()
