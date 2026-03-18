#!/bin/bash
cd /root/.openclaw/workspace/quant/quant

# 杀掉旧进程
pkill -f "gunicorn" 2>/dev/null
pkill -f "flask" 2>/dev/null
pkill -f "unified_server" 2>/dev/null
sleep 1

# 启动 gunicorn (API)
echo "Starting API server..."
gunicorn -w 1 -b 127.0.0.1:5000 'dashboard.api:app' --daemon
sleep 2

# 启动前端服务器 (Flask static)
echo "Starting frontend server..."
cd dashboard
python3 -c "
from unified_server import app
app.run(host='0.0.0.0', port=3000, debug=False)
" > /dev/null 2>&1 &

sleep 2
echo "Dashboard ready!"
echo "  API: http://127.0.0.1:5000"
echo "  Frontend: http://127.0.0.1:3000"
