"""
账户级风控模块
- 最大回撤熔断
- 每日亏损限制
- 连亏计数
"""
import json
import time
from datetime import datetime, timedelta


class AccountRiskController:
    """账户级风控"""
    
    def __init__(self, 
                 max_drawdown_pct=15,      # 最大回撤熔断 (15%)
                 daily_loss_pct=5,         # 每日亏损限制 (5%)
                 max_consecutive_losses=3, # 最大连亏次数
                 cooldown_minutes=60):     # 冷却时间
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_pct = daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_minutes = cooldown_minutes
        
        self.state_file = 'data/risk_state.json'
        self.state = self._load_state()
    
    def _load_state(self):
        """加载状态"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return {
                'peak_balance': 0,
                'current_balance': 0,
                'daily_pnl': 0,
                'daily_start': None,
                'consecutive_losses': 0,
                'last_loss_time': None,
                'circuit_breakers': [],
                'trading_paused': False,
                'pause_until': None
            }
    
    def _save_state(self):
        """保存状态"""
        import os
        os.makedirs('data', exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def update_balance(self, balance):
        """更新余额"""
        self.state['current_balance'] = balance
        
        if self.state['peak_balance'] == 0:
            self.state['peak_balance'] = balance
        
        if balance > self.state['peak_balance']:
            self.state['peak_balance'] = balance
        
        # 检查日期
        today = datetime.now().strftime('%Y-%m-%d')
        if self.state['daily_start'] != today:
            self.state['daily_pnl'] = 0
            self.state['daily_start'] = today
        
        self._save_state()
    
    def record_trade(self, pnl):
        """记录交易结果"""
        self.state['daily_pnl'] += pnl
        
        if pnl < 0:
            self.state['consecutive_losses'] += 1
            self.state['last_loss_time'] = time.time()
        else:
            self.state['consecutive_losses'] = 0
        
        self._check_risk()
        self._save_state()
    
    def _check_risk(self):
        """检查风险"""
        # 检查最大回撤
        if self.state['peak_balance'] > 0:
            drawdown = (self.state['peak_balance'] - self.state['current_balance']) / self.state['peak_balance'] * 100
            
            if drawdown >= self.max_drawdown_pct:
                self._trigger_circuit_breaker(f"Max drawdown reached: {drawdown:.1f}%")
                return
        
        # 检查每日亏损
        daily_loss = abs(self.state['daily_pnl'])
        if self.state['daily_pnl'] < 0 and daily_loss >= self.state['peak_balance'] * (self.daily_loss_pct / 100):
            self._trigger_circuit_breaker(f"Daily loss limit reached: {self.state['daily_pnl']:.2f}")
            return
        
        # 检查连亏
        if self.state['consecutive_losses'] >= self.max_consecutive_losses:
            # 检查是否在冷却期
            if self.state['last_loss_time']:
                elapsed = time.time() - self.state['last_loss_time']
                if elapsed < self.cooldown_minutes * 60:
                    self.state['trading_paused'] = True
                    self.state['pause_until'] = time.time() + self.cooldown_minutes * 60
                else:
                    # 冷却结束，重置连亏
                    self.state['consecutive_losses'] = 0
                    self.state['trading_paused'] = False
    
    def _trigger_circuit_breaker(self, reason):
        """触发熔断"""
        self.state['trading_paused'] = True
        self.state['circuit_breakers'].append({
            'time': datetime.now().isoformat(),
            'reason': reason
        })
        print(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")
    
    def can_trade(self):
        """是否可以交易"""
        # 检查是否暂停
        if self.state['trading_paused']:
            # 检查冷却是否结束
            if self.state.get('pause_until'):
                if time.time() > self.state['pause_until']:
                    self.state['trading_paused'] = False
                    self.state['consecutive_losses'] = 0
                    return True
            return False
        
        return True
    
    def get_status(self):
        """获取状态"""
        peak = self.state['peak_balance']
        current = self.state['current_balance']
        drawdown = (peak - current) / peak * 100 if peak > 0 else 0
        
        return {
            'can_trade': self.can_trade(),
            'peak_balance': peak,
            'current_balance': current,
            'drawdown_pct': drawdown,
            'daily_pnl': self.state['daily_pnl'],
            'consecutive_losses': self.state['consecutive_losses'],
            'paused': self.state['trading_paused']
        }
    
    def reset(self):
        """重置状态"""
        self.state = {
            'peak_balance': 0,
            'current_balance': 0,
            'daily_pnl': 0,
            'daily_start': datetime.now().strftime('%Y-%m-%d'),
            'consecutive_losses': 0,
            'last_loss_time': None,
            'circuit_breakers': [],
            'trading_paused': False,
            'pause_until': None
        }
        self._save_state()


if __name__ == '__main__':
    controller = AccountRiskController()
    
    # 模拟交易
    controller.update_balance(10000)
    controller.record_trade(-300)
    controller.record_trade(-200)
    controller.record_trade(-100)
    
    status = controller.get_status()
    print(f"Can trade: {status['can_trade']}")
    print(f"Drawdown: {status['drawdown_pct']:.2f}%")
    print(f"Consecutive losses: {status['consecutive_losses']}")
