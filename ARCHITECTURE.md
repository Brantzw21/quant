# Quant V2 量化交易系统 - 详细架构文档

**版本:** 2.0  
**更新日期:** 2026-02-27  
**维护者:** LH Quant Team

---

## 一、系统概述

### 1.1 项目定位
这是一个**多市场量化交易系统**，支持：
- **数字货币** (Binance合约) - 生产环境
- **A股** (沪深300等) - 回测/模拟
- **美股** - 开发中

### 1.2 核心能力
| 能力 | 说明 |
|------|------|
| 多策略回测 | 6种策略对比基准 |
| 风险指标分析 | 夏普/Sortino/Calar等 |
| 市场状态识别 | 趋势/震荡/高波动 |
| 账户级风控 | 回撤熔断/连亏冷却 |
| 实盘交易 | 数字货币永续合约 |

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           quant_v2 系统架构                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐ │
│  │   数据源层       │    │   策略引擎层      │    │   风控层         │ │
│  │                  │    │                  │    │                  │ │
│  │  • Binance(CCXT) │    │  • run_backtest  │    │  • risk_manager  │ │
│  │  • Baostock(A股) │    │  • 策略库        │    │  • risk_metrics  │ │
│  │  • yfinance(美股)│    │  • 参数优化器    │    │  • risk_controller│ │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘ │
│           │                       │                       │           │
│           └───────────────────────┼───────────────────────┘           │
│                                   │                                       │
│                    ┌──────────────▼──────────────┐                     │
│                    │       核心执行层 (quant_v2.py) │                   │
│                    │  • 策略Agent • 执行Agent • 监控  │                   │
│                    └──────────────────────────────┘                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构

```
quant_v2/
├── quant_v2.py              # 主入口 (实盘运行)
├── run_backtest.py          # 回测引擎 (含新风险指标)
│
├── ┌─────────────────────── 核心模块 ───────────────────────┐
│   │
│   ├── risk_metrics.py       # 风险指标计算 (新增)
│   │   • calculate_max_drawdown()
│   │   • calculate_sharpe_ratio()
│   │   • calculate_calmar_ratio()
│   │   • calculate_sortino_ratio()
│   │   • calculate_all_metrics()
│   │
│   ├── market_regime.py       # 市场状态识别 (新增)
│   │   • detect_market_regime()
│   │   • calculate_atr()
│   │   • get_dynamic_stop_loss()  # ATR动态止损
│   │   • get_dynamic_take_profit()
│   │
│   ├── risk_controller.py    # 账户级风控 (新增)
│   │   • 回撤熔断 (15%触发)
│   │   • 每日亏损限制 (5%触发)
│   │   • 连亏冷却 (3次后停60分钟)
│   │
│   ├── risk_manager.py       # 仓位与止损管理
│   │   • calculate_position_size()
│   │   • check_stop_loss()
│   │   • check_take_profit()
│   │   • check_risk_limits()
│   │
│   └── trading_monitor.py    # 交易监控
│
├── ┌────────────────────── 回测与优化 ──────────────────────┐
│   │
│   ├── backtest_framework.py  # 默认主回测框架 ⭐
│   ├── unified_backtest.py    # 多市场统一回测入口
│   ├── parameter_optimizer.py # 统一参数优化入口
│   ├── run_backtest.py        # 历史脚本 / 可逐步并轨
│   ├── portfolio_optimizer.py # 组合优化
│   └── position_sizer.py      # 仓位计算
│
├── ┌────────────────────── 策略库 ──────────────────────────┐
│   │
│   └── strategies/
│       ├── robust_rsi.py         # 稳健RSI策略 ⭐
│       ├── adaptive_rsi.py       # 自适应RSI
│       ├── layered_rsi.py        # 分层RSI
│       ├── trend_breakout.py     # 趋势突破
│       ├── weekly_strategy.py    # 周线策略
│       └── advanced_strategies.py # 高级策略合集
│
├── ┌────────────────────── 数据与指标 ──────────────────────┐
│   │
│   ├── indicators/           # 技术指标
│   │   └── technical_indicators.py
│   ├── factors/             # Alpha因子
│   │   └── alpha_factors.py
│   ├── brokers/             # 券商接口
│   │   ├── binance_broker.py
│   │   ├── ibkr_broker.py
│   │   └── futures_adapter.py
│   └── data/               # 数据存储
│       ├── last_signal.json
│       └── risk_state.json
│
├── ┌────────────────────── Agent模块 ──────────────────────┐
│   │
│   ├── strategy/agent.py    # 策略Agent
│   ├── execution/agent.py   # 执行Agent
│   ├── coder_agent.py      # 编码Agent
│   └── researcher_agent.py # 研究Agent
│
└── config/                  # 配置文件
```

---

## 四、核心模块详解

### 4.1 risk_metrics.py (风险指标)

**职责:** 计算策略的风险调整收益指标

```python
# 导出函数
from risk_metrics import (
    calculate_max_drawdown,   # 最大回撤
    calculate_annual_volatility, # 年化波动率
    calculate_sharpe_ratio,   # 夏普比率
    calculate_calmar_ratio,   # Calmar比率
    calculate_sortino_ratio,  # Sortino比率
    calculate_all_metrics     # 一次性计算全部
)
```

**计算逻辑:**
| 指标 | 公式 | 评价标准 |
|------|------|---------|
| 夏普比率 | (年化收益 - 无风险利率) / 年化波动率 | >1.0 优秀 |
| Sortino | (年化收益 - 无风险利率) / 下行波动率 | >1.0 优秀 |
| Calmar | 年化收益 / 最大回撤 | >1.0 优秀 |
| 最大回撤 | (峰值 - 谷底) / 峰值 | 越小越好 |

---

### 4.2 market_regime.py (市场状态)

**职责:** 识别当前市场环境，动态调整止损止盈

```python
# 市场状态
'trend_up'    # 上涨趋势
'trend_down'  # 下跌趋势
'range'       # 区间震荡
'volatile'    # 高波动
'neutral'     # 中性
```

**ATR动态止损:**
```python
# 根据市场状态调整止损距离
if market_regime == 'trend_up':
    stop_loss = entry - atr * 1.5   # 趋势中宽松
elif market_regime == 'volatile':
    stop_loss = entry - atr * 3      # 高波动更宽
else:
    stop_loss = entry - atr          # 震荡中紧凑
```

---

### 4.3 risk_controller.py (账户风控)

**职责:** 账户级别的风险保护机制

```
┌─────────────────────────────────────┐
│         风控触发流程                │
├─────────────────────────────────────┤
│                                     │
│  记录交易 → 检查风险 → 决定是否允许  │
│      ↓                              │
│  触发条件:                          │
│  1. 回撤 ≥ 15% → 熔断暂停           │
│  2. 日亏 ≥ 5%  → 熔断暂停           │
│  3. 连亏 ≥ 3次 → 冷却60分钟         │
│                                     │
└─────────────────────────────────────┘
```

**状态持久化:** `data/risk_state.json`

---

### 4.4 backtest_framework.py (默认主回测框架)

**职责:** 统一执行成本、权益曲线、参数优化、walk-forward 的主回测内核

**当前主链:**

```text
backtest_framework.py   -> 主回测内核
unified_backtest.py     -> 多市场统一入口
parameter_optimizer.py  -> 参数优化入口
```

**职责:** 多策略历史回测与风险分析

**支持策略:**
| 策略 | 逻辑 | 特点 |
|------|------|------|
| MA Cross | 5/20日均线交叉 | 基础趋势 |
| RSI | RSI超买超卖 | 均值回归 |
| Breakout | 20日高点突破 | 趋势追踪 |
| Dual MA+RSI | 均线+RSI共振 | 多指标过滤 |
| BB+RSI | 布林带+RSI | 波动率过滤 |
| 稳健RSI | 趋势过滤+MA50 | 延迟不敏感 ⭐ |

**输出指标:**
```
总收益 | 年化收益 | 夏普 | Sortino | Calmar | 最大回撤 | 波动率
```

---

## 五、数据流

### 5.1 回测流程

```
1. 获取数据 (Baostock/CCXT)
       ↓
2. 遍历每个策略
       ↓
3. 生成信号 (BUY/SELL/HOLD)
       ↓
4. 模拟交易 (计算仓位/成交)
       ↓
5. 计算 equity_curve
       ↓
6. risk_metrics 计算风险指标
       ↓
7. 输出结果 & 绘图
```

### 5.2 实盘流程

```
1. 获取实时行情
       ↓
2. 策略Agent分析 → 信号
       ↓
3. 风控检查 (risk_controller)
       ↓
4. 通过 → 执行Agent下单
       ↓
5. 成交记录 → 更新状态
       ↓
6. 监控检查 (trading_monitor)
       ↓
7. 循环 (每30分钟)
```

---

## 六、配置说明

### 6.1 config/__init__.py

```python
# 交易对
SYMBOL = "BTCUSDT"
LEVERAGE = 3

# 仓位
POSITION_PCT = 0.2          # 基础仓位20%
MAX_POSITION = 0.95         # 最大95%

# 风控
STOP_LOSS = 0.03            # 3%止损
TAKE_PROFIT = 0.08          # 8%止盈

# 监控
CHECK_INTERVAL = 1800       # 30分钟检查一次
```

### 6.2 风险参数

```python
# risk_manager.py
stop_loss_pct = 0.05        # 止损5%
take_profit_pct = 0.15     # 止盈15%
max_drawdown_pct = 0.20    # 最大回撤20%

# risk_controller.py
max_drawdown_pct = 0.15    # 熔断15%
daily_loss_pct = 0.05      # 日亏5%
max_consecutive_losses = 3 # 连亏3次
cooldown_minutes = 60      # 冷却60分钟
```

---

## 七、回测结果 (2023-01 ~ 2026-02)

### 7.1 策略对比

| 策略 | 总收益 | 年化收益 | 夏普 | Calmar | 最大回撤 | 波动率 |
|------|--------|----------|------|--------|----------|--------|
| **稳健RSI** | +13.2% | 437.8% | 0.20 | 0.51 | 8.6% | 6.6% |
| Dual MA+RSI | +8.1% | 269.9% | 0.02 | 0.18 | 14.6% | 10.9% |
| Breakout | +7.0% | 233.2% | -0.02 | 0.20 | 11.8% | 10.3% |
| BB+RSI | +0.4% | 12.0% | -0.40 | 0.01 | 8.5% | 6.6% |
| MA Cross | -0.0% | -1.1% | -0.19 | -0.00 | 18.5% | 12.2% |
| RSI | -4.0% | -133.0% | -0.39 | -0.06 | 21.1% | 9.9% |
| **沪深300(基准)** | **+21.1%** | - | - | - | - | - |

### 7.2 结论

1. **稳健RSI** 综合表现最佳（高收益+低回撤+低波动）
2. 所有策略目前跑输沪深300基准
3. 建议：优化策略参数 或 引入更多市场状态判断

---

## 八、使用指南

### 8.1 运行回测

```bash
cd /root/.openclaw/workspace/quant_v2

# 默认回测沪深300
python3 run_backtest.py

# 回测特定股票
python3 run_backtest.py --code sh.600519  # 茅台

# 调整参数
python3 run_backtest.py --capital 100000
```

### 8.2 运行实盘

```bash
# 持续运行
python3 quant_v2.py

# 单次运行
python3 quant_v2.py --once

# 查看状态
python3 quant_v2.py --status
```

---

## 九、依赖库

```
baostock          # A股数据
ccxt              # 数字货币交易所接口
pandas            # 数据处理
numpy             # 数值计算
matplotlib        # 绘图
requests          # HTTP请求
```

---

## 十、后续规划

- [ ] 集成ATR动态止损到实盘交易
- [ ] 优化稳健RSI参数
- [ ] 添加机器学习策略
- [ ] 支持组合多策略
- [ ] 添加模拟交易模式
- [ ] 美股数据源完善

---

**文档结束**
