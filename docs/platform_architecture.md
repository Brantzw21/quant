# 量化平台架构设计目标 (QuantConnect级别)

## 一、系统架构

```
Web Frontend (React)
       ↓
API Gateway (Flask)
       ↓
┌──────────────────────────────────────────┐
│ Strategy Hub │ Backtest │ Live Trading │
└──────────────────────────────────────────┘
       ↓
Data Manager (统一数据接口)
       ↓
A股数据 | 加密货币 | 外汇 | 因子数据
```

## 二、6大核心页面

1. **交易总览** - 账户概览
2. **策略管理** - 策略列表/编辑
3. **回测中心** - 回测/优化
4. **参数优化** - 自动搜索
5. **实盘交易** - 部署/监控
6. **风险监控** - 风控仪表盘

## 三、现有系统对比

| 模块 | 现有 | 目标 |
|------|------|------|
| Web前端 | Dashboard | ✅ 需增强 |
| 回测引擎 | unified_backtest.py | ✅ |
| 策略管理 | strategies/ | ✅ 需UI |
| 数据接口 | data_manager.py | ✅ |
| 风控 | risk_logger.py | ✅ 需UI |
| 参数优化 | parameter_optimizer.py | ✅ 需UI |

## 四、需要开发的UI

1. 参数优化页面
2. 组合回测页面
3. 策略编辑页面
4. 风险监控大屏

## 五、技术栈

- 前端: React + TradingView
- 后端: Flask/FastAPI
- 数据库: PostgreSQL + Redis (可选)
- 任务队列: Celery (可选)

## 六、开发优先级

| 优先级 | 页面 | 工作量 |
|--------|------|--------|
| P0 | 回测结果可视化 | 4小时 |
| P1 | 参数优化UI | 6小时 |
| P2 | 组合回测UI | 8小时 |
| P3 | 策略编辑UI | 8小时 |

---
设计参考: QuantConnect, Backtrader
