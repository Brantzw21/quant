#!/usr/bin/env python3
"""
Quant Dashboard 启动器
自动启动统一服务器（前端+API）
"""
import os
import sys
import subprocess
import signal
import time

# 项目路径
PROJECT_DIR = "/root/.openclaw/workspace/quant/quant"
DASHBOARD_DIR = f"{PROJECT_DIR}/dashboard"

def start_api():
    """启动后端API"""
    os.chdir(DASHBOARD_DIR)
    # 使用测试网
    os.environ['BINANCE_TESTNET'] = 'true'
    proc = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=DASHBOARD_DIR
    )
    print(f"API 启动: PID {proc.pid}")
    return proc

def start_frontend():
    """启动统一服务器"""
    os.chdir(DASHBOARD_DIR)
    proc = subprocess.Popen(
        [sys.executable, "unified_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=DASHBOARD_DIR
    )
    print(f"前端 启动: PID {proc.pid}")
    return proc

def main():
    print("=" * 40)
    print("Quant Dashboard 启动器")
    print("=" * 40)
    
    # 清理旧进程
    subprocess.run(["pkill", "-f", "unified_server"], stdout=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "dashboard/api.py"], stdout=subprocess.DEVNULL)
    time.sleep(1)
    
    # 启动服务
    api_proc = start_api()
    time.sleep(2)
    frontend_proc = start_frontend()
    
    print("")
    print("✅ 服务已启动:")
    print("   Dashboard: http://localhost:3000")
    print("   API: http://localhost:5000")
    print("")
    print("按 Ctrl+C 停止服务")
    print("=" * 40)
    
    # 等待
    try:
        api_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 停止服务...")
        api_proc.terminate()
        frontend_proc.terminate()
        print("✅ 已停止")

if __name__ == "__main__":
    main()
