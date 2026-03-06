# 量化系统回测功能分析文档

## 一、系统架构

```
unified_backtest.py    ← 统一回测入口
        ↓
strategy_adapter.py   ← 策略适配器
        ↓
data_manager.py      ← 数据获取 (A股/币/外汇)
```

## 二、支持的市场

| 市场 | 数据源 | 状态 |
|------|--------|------|
| A股 | Baostock | ✅ |
| 加密货币 | Binance | ✅ |
| 外汇 | Yahoo | ✅ |

## 三、支持策略 (19个)

1. 动量策略 momentum
2. 海龟策略 turtle
3. 均线交叉 ma_cross
4. MACD macd
5. 突破策略 breakout
6. 通道突破 channel
7. 周线策略 weekly
8. RSI均值回归 rsi
9. 布林回归 bollinger
10. KDJ kdj
... 等

## 四、回测结果 (2021-2026)

### A股 (创业板)

| 策略 | 收益 | 交易次数 |
|------|------|----------|
| 动量 | +98.7% | 27次 |
| 海龟 | +95.1% | 31次 |
| 通道 | +96.1% | 25次 |
| MACD | +72.1% | 77次 |
| 均线 | +62.4% | 69次 |

### 加密货币 (BTC)

| 策略 | 收益 | 交易次数 |
|------|------|----------|
| 动量 | -27.0% | 20次 |
| 均线 | -13.8% | 15次 |

## 五、使用方法

```bash
# 单市场单策略
python3 unified_backtest.py -m a_stock -s sz.399006 --strategy momentum

# 对比所有策略
python3 unified_backtest.py -m a_stock -s sz.399006 --compare
```

## 六、API接口

| 接口 | 功能 |
|------|------|
| /api/backtest | 回测 |
| /api/backtest/optimize | 参数优化 |
| /api/backtest/walkforward | Walk-Forward |
| /api/portfolio | 组合 |

## 七、评分

| 维度 | 评分 |
|------|------|
| 功能完整 | ⭐⭐⭐⭐ |
| 多市场 | ⭐⭐⭐⭐⭐ |
| 稳定性 | ⭐⭐⭐⭐ |
| 易用性 | ⭐⭐⭐⭐ |

**综合: 85/100**

---
生成时间: 2026-03-06
