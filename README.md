# LH Quant 量化交易系统 - 项目文档

## 一、项目概述

### 1.1 系统定位
这是一个**数字货币量化交易系统**，专门用于交易 Binance 的 BTC/USDT 合约。

### 1.2 支持的市场
| 市场 | 数据源 | 状态 |
|------|--------|------|
| 虚拟货币 | Binance CCXT | ✅ 生产使用 |
| A股 | baostock | 🔧 开发中 |
| 美股 | yfinance | 🔧 开发中 |

---

## 二、系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     quant_v2 (生产系统)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │ 策略Agent   │ ──→ │  执行Agent  │ ──→ │  监控Agent │  │
│   │ (Signal)    │ JSON │ (Trade)    │     │ (Monitor)  │  │
│   └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                    共享资源                           │   │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│   │  │ brokers │  │strategies│  │indicators│              │   │
│   │  └─────────┘  └─────────┘  └─────────┘              │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
quant_v2/
├── quant_v2.py           # 主入口 (策略+执行+监控+回测)
├── config/               # 配置文件
│   └── __init__.py
├── strategy/            # 策略Agent
│   └── agent.py
├── execution/           # 执行Agent
│   └── agent.py
├── brokers/             # 券商接口 (链接至quant/brokers)
├── strategies/          # 策略库 (链接至quant/strategies)
├── indicators/          # 技术指标 (链接至quant/indicators)
├── factors/             # Alpha因子 (链接至quant/factors)
├── logs/                # 交易日志
│   └── trades.json
└── data/                # 数据与状态
    ├── last_signal.json
    └── risk_state.json
```

---

## 三、各模块功能

### 3.1 策略Agent (strategy/agent.py)

**职责：** 分析市场，生成交易信号

**输入：**
- Binance 1小时K线
- Binance 4小时K线

**处理流程：**
```
获取数据 → 计算指标 → 多指标共识 → 输出信号
```

**技术指标：**
| 指标 | 类型 | 用途 |
|------|------|------|
| MA10/MA20/MA50 | 趋势 | 判断多空 |
| RSI | 动量 | 超买超卖 |
| MACD | 动量 | 金叉死叉 |
| 布林带 | 波动 | 突破信号 |

**信号逻辑：**
- BUY：≥2个指标同时看涨
- SELL：≥2个指标同时看跌
- HOLD：其他情况

**附加过滤：**
- 高波动市场(>3%)禁止交易

### 3.2 执行Agent (execution/agent.py)

**职责：** 接收信号，执行交易，风控管理

**风控规则：**
| 规则 | 参数 |
|------|------|
| 每日最大交易 | 5次 |
| 连亏限制 | 3次后冷却60分钟 |
| 最小交易金额 | 100 USDT |
| 止损 | 3% |
| 止盈 | 8% |

**仓位计算：**
- 凯利公式 (Kelly Criterion)
- 基础仓位20%
- 连亏后减半

### 3.3 监控Agent (Monitor)

**职责：** 检查系统健康状态

**检查项：**
- 进程运行状态
- 账户余额
- 持仓情况
- 交易日志
- 信号文件

---

## 四、策略详情

### 4.1 当前策略：多指标共识

```python
# 信号收集
signals = []

# 1. 趋势信号
if ma10 > ma50: signals.append("BUY")

# 2. RSI信号  
if rsi < 30: signals.append("BUY")

# 3. MACD信号
if macd > macd_signal: signals.append("BUY")

# 4. 布林信号
if price > upper: signals.append("BUY")

# 共识决策
if signals.count("BUY") >= 2:
    action = "BUY"
```

### 4.2 回测结果 (6年数据)

| 指标 | 值 |
|------|------|
| 回测周期 | 2020-02 ~ 2026-02 (6年) |
| 数据量 | 52,534条1小时K线 |
| 初始资金 | $10,000 |
| 最终资金 | $40,816 |
| **总收益** | **+408.16%** |
| 交易次数 | 373次 |
| 胜率 | 34.6% |
| 止损 | 3% |
| 止盈 | 8% |

**对比：**
- 策略收益：+408%
- 持有BTC：+679%

---

## 五、回测主链（2026-03 更新）

### 5.1 默认回测框架

当前项目的默认回测主链已经统一为：

```text
backtest_framework.py   # 唯一主回测框架
unified_backtest.py     # 多市场统一回测入口
parameter_optimizer.py  # 统一参数优化入口
```

### 5.2 模块定位

| 文件 | 定位 | 说明 |
|------|------|------|
| `backtest_framework.py` | 主框架 | 默认唯一回测内核 |
| `unified_backtest.py` | 入口层 | 多市场/多策略统一调用主框架 |
| `parameter_optimizer.py` | 优化层 | 基于主框架做真实参数搜索 |
| `dashboard/enhanced_backtest.py` | API层 | Dashboard 回测接口，底层调用主框架 |
| `backtest_engine.py` | 兼容层 | 为历史导入保留，不再作为新开发主入口 |

### 5.3 开发约定

- 新增回测能力，默认改 `backtest_framework.py`
- 新增多市场调用或策略对比，默认改 `unified_backtest.py`
- 新增参数搜索能力，默认改 `parameter_optimizer.py`
- 不再新增独立回测引擎脚本，避免再次出现多套实现分叉

## 六、使用指南

### 5.1 启动命令

```bash
# 进入目录
cd /root/.openclaw/workspace/quant_v2

# 持续运行 (默认)
python3 quant_v2.py

# 单次运行
python3 quant_v2.py --once

# 查看状态
python3 quant_v2.py --status

# 回测
python3 quant_v2.py --backtest
```

### 5.2 配置修改

编辑 `config/__init__.py`：

```python
# API配置
API_KEY = "your_api_key"
SECRET_KEY = "your_secret"
TESTNET = True  # True=测试网, False=实盘

# 交易配置
SYMBOL = "BTCUSDT"
LEVERAGE = 3
POSITION_PCT = 0.2

# 风控
STOP_LOSS = 0.03
TAKE_PROFIT = 0.08
CHECK_INTERVAL = 1800  # 30分钟
```

---

## 六、数据说明

### 6.1 市场区分

| 市场 | 特点 | 数据源 |
|------|------|--------|
| **虚拟货币** | 24/7交易 | Binance CCXT |
| A股 | 有周末收盘 | baostock |
| 美股 | 有交易时段 | yfinance |

**注意：** 当前系统专为虚拟货币设计，其他市场需单独适配。

### 6.2 数据获取

```python
# CCXT分页获取
since = 6年前时间戳
while True:
    data = exchange.fetch_ohlcv('BTC/USDT', '1h', since=since)
    if len(data) < 1000:
        break
    since = data[-1][0] + 1
```

---

## 七、注意事项

1. **API安全：** 实盘请设置IP白名单，只开交易权限
2. **风险：** 合约交易杠杆高，请控制仓位
3. **监控：** 定期检查日志和持仓
4. **备份：** 重要配置和日志定期备份

---

## 八、联系与支持

- 系统版本：v2.0
- 更新时间：2026-02-26
- 架构：Multi-Agent
