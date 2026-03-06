"""
可视化模块 - 封装matplotlib绘图功能
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ChartBuilder:
    """图表构建器"""
    
    def __init__(self, title="图表"):
        self.fig = None
        self.axes = []
        self.title = title
        self.data = None
    
    def set_data(self, data):
        """设置数据"""
        self.data = data
        return self
    
    def candle(self, data=None):
        """K线图"""
        if data is None:
            data = self.data
        if data is None:
            raise ValueError("请先设置数据")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 转换时间
        if 'datetime' in data[0]:
            dates = [d['datetime'] for d in data]
        else:
            dates = range(len(data))
        
        # 绘制K线
        for i, d in enumerate(data[-50:]):  # 只显示最近50根
            o, h, l, c = d['open'], d['high'], d['low'], d['close']
            color = 'red' if c >= o else 'green'
            ax.plot([i, i], [l, h], color=color, linewidth=0.5)
            ax.plot([i-0.3, i+0.3], [o, o], color=color, linewidth=0.5)
            ax.plot([i-0.3, i+0.3], [c, c], color=color, linewidth=0.5)
        
        ax.set_title(f"{self.title} - K线")
        ax.set_xlabel("时间")
        ax.set_ylabel("价格")
        ax.grid(True, alpha=0.3)
        
        self.fig = fig
        self.axes = [ax]
        return self
    
    def add_ma(self, periods=[5, 20, 60]):
        """添加均线"""
        if not self.axes:
            return self
        
        ax = self.axes[0]
        closes = [d['close'] for d in self.data]
        
        colors = ['yellow', 'blue', 'purple']
        for i, p in enumerate(periods):
            if len(closes) >= p:
                ma = np.convolve(closes, np.ones(p)/p, mode='valid')
                ax.plot(range(len(closes)-len(ma)+1, len(closes)+1), 
                       ma, label=f'MA{p}', color=colors[i%len(colors)], linewidth=1)
        
        ax.legend()
        return self
    
    def add_rsi(self, period=14):
        """添加RSI"""
        if not self.axes:
            return self
        
        if len(self.axes) < 2:
            fig, ax2 = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
            self.fig = fig
            self.axes = [ax2[0], ax2[1]]
            # 重新绘制K线到ax[0]
            ax = self.axes[0]
            closes = [d['close'] for d in self.data[-50:]]
            ax.plot(closes, 'k-', linewidth=0.5)
        
        ax = self.axes[1]
        closes = [d['close'] for d in self.data]
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        ax.plot(rsi, 'b-', linewidth=1)
        ax.axhline(70, color='r', linestyle='--', alpha=0.5)
        ax.axhline(30, color='g', linestyle='--', alpha=0.5)
        ax.set_ylabel('RSI')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        return self
    
    def equity_curve(self, equity_data, benchmark=None, name="策略"):
        """资产曲线图"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 策略曲线
        ax.plot(equity_data, label=name, linewidth=2, color='blue')
        
        # 基准曲线
        if benchmark is not None:
            ax.plot(benchmark, label='基准', linewidth=1.5, color='gray', linestyle='--')
        
        ax.set_title(f"{self.title} - 资产曲线")
        ax.set_xlabel("时间")
        ax.set_ylabel("资产")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.fig = fig
        self.axes = [ax]
        return self
    
    def add_signals(self, signals):
        """添加信号标记"""
        if not self.axes:
            return self
        
        ax = self.axes[0]
        
        for i, sig in enumerate(signals):
            if sig == 'BUY':
                ax.axvline(i, color='green', linestyle='--', alpha=0.5)
            elif sig == 'SELL':
                ax.axvline(i, color='red', linestyle='--', alpha=0.5)
        
        return self
    
    def show(self):
        """显示图表"""
        if self.fig:
            plt.tight_layout()
            plt.show()
        return self
    
    def save(self, filepath, dpi=150):
        """保存图表"""
        if self.fig:
            plt.tight_layout()
            plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
            print(f"图表已保存: {filepath}")
        return self


def plot_backtest_result(results, index_equity, name="回测"):
    """
    绘制回测结果
    
    Args:
        results: 回测结果列表
        index_equity: 基准收益曲线
        name: 基准名称
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 资产曲线
    ax1 = axes[0, 0]
    for r in results:
        ax1.plot(r["equity_curve"], label=r["name"], color=r.get("color", "blue"), linewidth=1.5)
    if index_equity:
        ax1.plot(index_equity, label=name, color='gray', linestyle='--', linewidth=1.5)
    ax1.set_title("资产曲线")
    ax1.set_xlabel("时间")
    ax1.set_ylabel("资产")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 最大回撤
    ax2 = axes[0, 1]
    names = [r["name"] for r in results]
    max_dds = [r.get("max_drawdown", 0) * 100 for r in results]
    colors = ['red' if d > 10 else 'orange' if d > 5 else 'green' for d in max_dds]
    ax2.barh(names, max_dds, color=colors)
    ax2.set_title("最大回撤 (%)")
    ax2.set_xlabel("回撤 (%)")
    ax2.grid(True, alpha=0.3)
    
    # 夏普比率
    ax3 = axes[1, 0]
    sharpes = [r.get("sharpe_ratio", 0) for r in results]
    colors = ['green' if s > 1 else 'orange' if s > 0 else 'red' for s in sharpes]
    ax3.barh(names, sharpes, color=colors)
    ax3.set_title("夏普比率")
    ax3.set_xlabel("夏普比率")
    ax3.grid(True, alpha=0.3)
    
    # 收益对比
    ax4 = axes[1, 1]
    returns = [r.get("total_return", 0) * 100 for r in results]
    colors = ['green' if r > 0 else 'red' for r in returns]
    ax4.barh(names, returns, color=colors)
    ax4.set_title("总收益 (%)")
    ax4.set_xlabel("收益 (%)")
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def plot_equity_with_signals(equity_curve, trades, title="交易记录"):
    """绘制带交易信号的资产曲线"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # 资产曲线
    ax.plot(equity_curve, 'b-', linewidth=1.5, label='资产')
    
    # 标记买卖点
    buy_points = []
    sell_points = []
    
    for i, trade in enumerate(trades):
        if trade.get('action') == 'BUY':
            buy_points.append((i, equity_curve[i] if i < len(equity_curve) else equity_curve[-1]))
        elif trade.get('action') == 'SELL':
            sell_points.append((i, equity_curve[i] if i < len(equity_curve) else equity_curve[-1]))
    
    if buy_points:
        ax.scatter([p[0] for p in buy_points], [p[1] for p in buy_points], 
                  marker='^', color='green', s=100, label='买入', zorder=5)
    if sell_points:
        ax.scatter([p[0] for p in sell_points], [p[1] for p in sell_points], 
                  marker='v', color='red', s=100, label='卖出', zorder=5)
    
    ax.set_title(title)
    ax.set_xlabel("交易次数")
    ax.set_ylabel("资产")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


if __name__ == '__main__':
    # 测试
    print("可视化模块测试")
    print("使用: ChartBuilder(symbol).candle().add_ma([5,20]).show()")
