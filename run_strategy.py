#!/usr/bin/env python3
"""
定时更新策略信号
每30分钟运行一次 (轻量版)
"""

import sys
import os
import json
sys.path.insert(0, '/root/.openclaw/workspace/quant_v2')

from light_strategy import generate_signal
from notify import notify_signal_change
from datetime import datetime

def run_strategy():
    """执行策略并生成信号"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始生成信号...")
    
    # 读取旧信号
    signal_file = '/root/.openclaw/workspace/quant_v2/data/last_signal.json'
    old_signal = 'N/A'
    try:
        with open(signal_file, 'r') as f:
            old_data = json.load(f)
            old_signal = old_data.get('signal', 'N/A')
    except:
        pass
    
    try:
        new_signal = generate_signal()
        
        # 检测信号变化并推送
        notify_signal_change(new_signal, old_signal)
        
        print(f"信号生成完成: {new_signal.get('signal', 'N/A')}")
        return True
    except Exception as e:
        print(f"策略执行失败: {e}")
        return False

if __name__ == "__main__":
    run_strategy()
