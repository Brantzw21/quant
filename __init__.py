"""
LH Quant v2.0 - 量化交易系统
=============================

双Agent架构:
- Strategy Agent: 负责分析市场、生成信号
- Execution Agent: 负责执行交易、风控管理

目录结构:
  quant_v2/
  ├── strategy/      # 策略Agent
  ├── execution/     # 执行Agent
  ├── config/       # 配置文件
  ├── logs/         # 日志
  └── data/         # 数据

作者: AutoQuant
"""

import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")

# 确保目录存在
for d in [CONFIG_DIR, LOG_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

print(f"""
╔══════════════════════════════════════════════╗
║         LH Quant v2.0 架构                   ║
╠══════════════════════════════════════════════╣
║  quant_v2/                                   ║
║  ├── strategy/    # 策略Agent (信号生成)     ║
║  ├── execution/   # 执行Agent (交易、风控)    ║
║  ├── config/     # 配置文件                  ║
║  ├── logs/       # 日志文件                  ║
║  └── data/       # 数据存储                  ║
╚══════════════════════════════════════════════╝
""")
