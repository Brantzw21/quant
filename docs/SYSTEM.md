# 量化交易系统 Quant V2 完整文档

## 一、系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Quant V2 量化交易系统                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │   前端 UI   │    │   后端 API  │    │  策略引擎   │    │   数据层    │ │
│   │ (React)     │◄──►│  (Flask)    │◄──►│ (Python)   │◄──►│ (Binance)   │ │
│   │  端口 3000  │    │  端口 5001  │    │             │    │             │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块详解

### 2.1 数据层 (Data Layer)

```
data_manager.py      - 多数据源获取 (Binance API)
data_feeder.py       - 数据标准化处理
data_backup.py       - 数据备份导出
```

**功能：**
- 从 Binance 获取 K 线数据
- 支持多周期：1m, 5m, 15m, 1h, 4h, 1d, 1w
- 数据清洗和标准化

---

### 2.2 策略层 (Strategy Layer)

```
light_strategy.py    - 主策略 (RSI + MA + ADX + ATR)
```

**策略逻辑：**

| 指标 | 说明 |
|------|------|
| MA(10/20/50) | 移动平均线判断趋势 |
| RSI(14) | 相对强弱指标，RSI<40 超卖，RSI>60 超买 |
| ADX(14) | 趋势强度指标，ADX>20 表示趋势明显 |
| ATR(14) | 平均真实波幅，用于动态止盈止损 |

**信号生成规则：**

```
买入条件 (LONG):
├── 多周期共振: 周线+日线+4h 同时看多
├── ADX > 20 (趋势强度足够)
├── 成交量 > 1.5x 均线 (量价配合)
└── RSI < 40 (超卖)

卖出条件 (SHORT):
├── 多周期共振: 周线+日线+4h 同时看空
├── ADX > 20
├── 成交量 > 1.5x 均线
└── RSI > 60 (超买)
```

**ATR 动态止盈止损：**
- 止损：入场价 - 1.5 × ATR
- 止盈：入场价 + 3 × ATR

---

### 2.3 风控层 (Risk Control)

```
risk_control.py      - 风控规则集合
```

**风控规则：**

| 规则 | 参数 | 说明 |
|------|------|------|
| 持仓限制 | ≤50% | 最大持仓比例 |
| 单笔限制 | 20% | 单笔仓位比例 |
| 回撤熔断 | 20% | 最大回撤限制 |
| 日内交易 | ≤10次 | 每日最大交易次数 |

---

### 2.4 执行层 (Execution)

```
brokers/binance_broker.py  - Binance 接口
```

**执行参数：**
- 手续费：0.04%
- 滑点：0.05%
- 最小成交额：5 USDT

---

### 2.5 回测引擎 (Backtest Engine)

```
backtest_engine.py   - 回测主引擎
position_sizer.py    - 仓位计算
execution_simulator.py - 执行模拟
```

**分层架构：**

```
backtest_engine (主控)
     ↓
strategy_agent (策略信号)
     ↓
risk_manager (ATR 动态止盈止损)
     ↓
position_sizer (比例仓位 20%)
     ↓
execution_simulator (手续费+滑点)
```

**回测特性：**
- ✅ 手续费 0.04%
- ✅ 滑点 0.05%
- ✅ 比例仓位 20%
- ✅ ATR 动态止盈止损
- ✅ 权益曲线计算
- ✅ 最大回撤计算
- ✅ Sharpe 比率

---

### 2.6 账户管理

```
account.py           - 账户状态查询
portfolio.py         - 组合管理
```

---

### 2.7 监控与通知

```
monitor.py           - 系统监控
notify.py            - 消息通知
```

---

## 三、前端 Dashboard

```
dashboard/
├── src/
│   ├── App.jsx          - 主应用 (React)
│   ├── components/       - 组件
│   │   ├── Sidebar.jsx
│   │   ├── TopBar.jsx
│   │   ├── EquityChart.jsx
│   │   ├── RiskPanel.jsx
│   │   └── LogPanel.jsx
│   └── main.jsx
├── api.py               - Flask API (端口 5001)
└── vite.config.js       - Vite 配置 (端口 3000)
```

**页面功能：**

| 页面 | 功能 |
|------|------|
| Dashboard | 仪表盘，权益曲线，信号显示 |
| Wallets | 钱包资产 (实盘/模拟盘切换) |
| Monitor | 监控面板 |
| Strategies | 策略管理 |
| Backtest | 回测分析 |
| Risk Center | 风控指标 |

---

## 四、配置文件

```
config/
├── __init__.py          - 主配置
│   ├── API_KEY          - 模拟盘 Key
│   ├── SECRET_KEY       - 模拟盘 Secret
│   ├── REAL_API_KEY     - 实盘 Key
│   ├── REAL_SECRET_KEY  - 实盘 Secret
│   ├── TESTNET = True   - 测试网开关
│   ├── SYMBOL = BTCUSDT
│   ├── LEVERAGE = 3x
│   └── POSITION_PCT = 20%
│
├── strategy_params.yaml - 策略参数
├── exchange.yaml        - 交易所配置
└── system.yaml          - 系统配置
```

---

## 五、API 接口

| 接口 | 说明 |
|------|------|
| `/api/account` | 账户信息 |
| `/api/positions` | 持仓 |
| `/api/orders` | 订单 |
| `/api/wallets` | 钱包资产 (?type=simulate/real) |
| `/api/signal` | 当前信号 |
| `/api/risk` | 风控状态 |
| `/api/performance` | 绩效 |
| `/api/equity` | 权益历史 |

---

## 六、部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                         服务器                               │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │  Systemd        │    │  Dashboard                  │   │
│  │  quant-dashboard│    │  Flask :5001 + Vite :3000   │   │
│  │  服务           │    │  (systemd 托管)             │   │
│  └─────────────────┘    └─────────────────────────────┘   │
│                                                              │
│  ┌─────────────────┐                                       │
│  │  Quant 策略     │                                       │
│  │  auto_trade.py │                                       │
│  │  (Cron 定时)   │                                       │
│  └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、运行指令

```bash
# 启动后端 API
systemctl start quant-dashboard

# 查看状态
systemctl status quant-dashboard

# 手动运行策略
cd /root/.openclaw/workspace/quant_v2
python3 light_strategy.py

# 运行回测
python3 backtest_engine.py
```

---

## 八、数据流向

```
Binance API
    ↓
data_manager (获取数据)
    ↓
light_strategy (生成信号)
    ↓
risk_control (风控检查)
    ↓
binance_broker (执行交易)
    ↓
account (更新持仓)
    ↓
dashboard API (前端展示)
    ↓
React UI
```

---

## 九、版本信息

- **版本**: V2.0.0
- **更新日期**: 2026-03-05
- **主要特性**:
  - 多周期趋势共振
  - ADX 趋势过滤
  - ATR 动态止盈止损
  - 成交量确认
  - 完整回测框架
