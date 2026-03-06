#!/bin/bash
cd /root/.openclaw/workspace/quant/quant

# 杀掉旧进程
pkill -f "gunicorn" 2>/dev/null
pkill -f "unified_server" 2>/dev/null
sleep 1

# 启动gunicorn (API)
gunicorn -w 1 -b 127.0.0.1:5000 'dashboard.api:app' > /dev/null 2>&1 &
echo "API started: $(date)"

# 启动统一服务器
cd dashboard
python3 unified_server.py > /dev/null 2>&1 &
echo "Frontend started: $(date)"

sleep 2
echo "Dashboard ready!"
