#!/bin/bash
cd /root/.openclaw/workspace/quant_v2

# 获取周报
REPORT=$(curl -s http://localhost:5000/api/report/weekly)

# 发送到飞书（如果配置了）
python3 -c "
import json, sys
sys.path.insert(0, '.')
from notify import notify_weekly_report

data = json.loads('''$REPORT''')
if data.get('success'):
    notify_weekly_report(data.get('report', {}))
    print('✅ 周报已发送')
else:
    print('❌ 周报获取失败')
"

echo "$(date): Weekly report sent" >> /tmp/weekly_report.log
