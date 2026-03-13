import { useMemo, useState } from "react";
import { Play, RotateCcw, TrendingUp } from "lucide-react";

const strategyOptions = [
  { value: "momentum", label: "Momentum 动量" },
  { value: "ma_cross", label: "MA Cross 均线交叉" },
  { value: "macd", label: "MACD" },
  { value: "turtle", label: "Turtle 海龟" },
  { value: "breakout", label: "Breakout 趋势突破" },
  { value: "channel", label: "Channel 通道突破" },
  { value: "weekly", label: "Weekly 周线趋势" },
];

const marketOptions = [
  { value: "crypto", label: "加密货币", symbols: ["BTCUSDT", "ETHUSDT"] },
  { value: "a_stock", label: "A股", symbols: ["sh.000300", "sz.399006"] },
  { value: "us_stock", label: "美股", symbols: ["SPY", "AAPL"] },
];

const defaultOptimizationGrid = {
  momentum: { lookback: [10, 20, 30], threshold: [0.03, 0.05, 0.08] },
  ma_cross: { fast: [5, 10, 15], slow: [20, 30, 50] },
  macd: { fast: [8, 12], slow: [21, 26], signal: [7, 9] },
  turtle: { entry_period: [20, 30], exit_period: [10, 15] },
  breakout: { lookback: [20, 30, 40] },
  channel: { period: [15, 20, 30] },
  weekly: { ma_period: [8, 10, 12] },
};

const cardCls = "bg-zinc-800 rounded-lg p-4 border border-zinc-700";

const BacktestEnhanced = () => {
  const [config, setConfig] = useState({
    market: "crypto",
    symbol: "BTCUSDT",
    start_date: "2024-01-01",
    end_date: "2026-03-01",
    initial_capital: 100000,
    fee: 0.001,
    slippage: 5,
    strategy: "momentum",
    train_size: 120,
    test_size: 40,
    step_size: 40,
  });
  const [mode, setMode] = useState("backtest");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const currentSymbols = useMemo(() => {
    return marketOptions.find((item) => item.value === config.market)?.symbols || [];
  }, [config.market]);

  const normalizeResults = (kind, payload) => {
    if (!payload || payload.success === false) {
      throw new Error(payload?.error || "请求失败");
    }

    if (kind === "backtest") {
      return {
        kind,
        totalReturn: payload.total_return,
        sharpeRatio: payload.stats?.sharpe_ratio,
        maxDrawdown: payload.stats?.max_drawdown,
        winRate: payload.stats?.win_rate,
        profitFactor: payload.stats?.profit_factor,
        totalTrades: payload.stats?.total_trades,
        equityCurve: payload.equity_curve || [],
        returnsCurve: payload.returns_curve || [],
        trades: payload.trades || [],
        strategyName: payload.strategy_name,
        dataSource: payload.data_source,
      };
    }

    if (kind === "optimize") {
      return {
        kind,
        strategyName: payload.strategy_name,
        totalCombinations: payload.total_combinations,
        bestParams: payload.best_params,
        rows: payload.all_results || [],
      };
    }

    return {
      kind,
      strategyName: payload.strategy_name,
      passRatio: payload.pass_ratio,
      wfScore: payload.wf_score,
      avgTotalReturn: payload.avg_total_return,
      avgMaxDrawdown: payload.avg_max_drawdown,
      avgSharpeRatio: payload.avg_sharpe_ratio,
      rows: payload.periods || [],
    };
  };

  const postJson = async (url, payload, kind) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setMode(kind);
      setResults(normalizeResults(kind, data));
    } catch (e) {
      setError(e.message || "请求失败");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = () => {
    postJson("/api/enhanced/backtest", config, "backtest");
  };

  const runOptimization = () => {
    postJson(
      "/api/backtest/optimize",
      {
        ...config,
        param_grid: defaultOptimizationGrid[config.strategy] || {},
      },
      "optimize"
    );
  };

  const runWalkForward = () => {
    postJson("/api/backtest/walkforward", config, "walkforward");
  };

  return (
    <div className="space-y-4">
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs text-zinc-400 mb-1">市场</label>
          <select
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.market}
            onChange={(e) => {
              const market = e.target.value;
              const fallback = marketOptions.find((item) => item.value === market)?.symbols?.[0] || "BTCUSDT";
              setConfig({ ...config, market, symbol: fallback });
            }}
          >
            {marketOptions.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">交易品种</label>
          <select
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.symbol}
            onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
          >
            {currentSymbols.map((symbol) => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">策略</label>
          <select
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.strategy}
            onChange={(e) => setConfig({ ...config, strategy: e.target.value })}
          >
            {strategyOptions.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">初始资金</label>
          <input
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.initial_capital}
            onChange={(e) => setConfig({ ...config, initial_capital: Number(e.target.value) })}
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">开始日期</label>
          <input
            type="date"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.start_date}
            onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">结束日期</label>
          <input
            type="date"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.end_date}
            onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">手续费</label>
          <input
            type="number"
            step="0.0001"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.fee}
            onChange={(e) => setConfig({ ...config, fee: Number(e.target.value) })}
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">滑点 (bp)</label>
          <input
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.slippage}
            onChange={(e) => setConfig({ ...config, slippage: Number(e.target.value) })}
          />
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-zinc-400 mb-1">Train Size</label>
          <input
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.train_size}
            onChange={(e) => setConfig({ ...config, train_size: Number(e.target.value) })}
          />
        </div>
        <div>
          <label className="block text-xs text-zinc-400 mb-1">Test Size</label>
          <input
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.test_size}
            onChange={(e) => setConfig({ ...config, test_size: Number(e.target.value) })}
          />
        </div>
        <div>
          <label className="block text-xs text-zinc-400 mb-1">Step Size</label>
          <input
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.step_size}
            onChange={(e) => setConfig({ ...config, step_size: Number(e.target.value) })}
          />
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={runBacktest} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm disabled:opacity-50">
          <Play size={16} /> 运行回测
        </button>
        <button onClick={runOptimization} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm disabled:opacity-50">
          <RotateCcw size={16} /> 参数优化
        </button>
        <button onClick={runWalkForward} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm disabled:opacity-50">
          <TrendingUp size={16} /> Walk Forward
        </button>
      </div>

      {error && <div className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">{error}</div>}
      {loading && <div className="text-center py-8 text-zinc-400">运行中...</div>}

      {results?.kind === "backtest" && (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className={cardCls}>
              <div className="text-xs text-zinc-400">总收益率</div>
              <div className={`text-2xl font-bold ${(results.totalReturn || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {results.totalReturn?.toFixed(2)}%
              </div>
            </div>
            <div className={cardCls}>
              <div className="text-xs text-zinc-400">夏普比率</div>
              <div className="text-2xl font-bold text-cyan-400">{results.sharpeRatio?.toFixed(3)}</div>
            </div>
            <div className={cardCls}>
              <div className="text-xs text-zinc-400">最大回撤</div>
              <div className="text-2xl font-bold text-red-400">{results.maxDrawdown?.toFixed(2)}%</div>
            </div>
            <div className={cardCls}>
              <div className="text-xs text-zinc-400">胜率</div>
              <div className="text-2xl font-bold text-yellow-400">{results.winRate?.toFixed(2)}%</div>
            </div>
          </div>

          <div className={cardCls}>
            <div className="text-sm font-bold mb-2">回测摘要</div>
            <div className="grid md:grid-cols-2 gap-2 text-sm text-zinc-300">
              <div>策略: {results.strategyName}</div>
              <div>数据源: {results.dataSource}</div>
              <div>盈利因子: {results.profitFactor?.toFixed(3)}</div>
              <div>交易次数: {results.totalTrades}</div>
            </div>
          </div>

          <div className={cardCls}>
            <div className="text-sm font-bold mb-2">权益曲线</div>
            <div className="h-48 flex items-end gap-1">
              {results.equityCurve.slice(0, 120).map((item, i) => {
                const values = results.equityCurve.map((v) => v.equity);
                const min = Math.min(...values);
                const max = Math.max(...values);
                const height = max === min ? 40 : ((item.equity - min) / (max - min)) * 100;
                return <div key={i} className="flex-1 bg-green-500/80 rounded-t-sm" style={{ height: `${Math.max(height, 4)}%` }} />;
              })}
            </div>
          </div>
        </>
      )}

      {results?.kind === "optimize" && (
        <div className={cardCls}>
          <div className="flex justify-between items-center mb-3">
            <div>
              <div className="text-sm font-bold">参数优化结果</div>
              <div className="text-xs text-zinc-400">{results.strategyName}</div>
            </div>
            <div className="text-xs text-zinc-400">组合数: {results.totalCombinations}</div>
          </div>
          <div className="text-xs text-green-400 mb-2">最佳参数: {JSON.stringify(results.bestParams)}</div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-700">
                  <th className="text-left py-2">参数</th>
                  <th className="text-right">收益率</th>
                  <th className="text-right">夏普</th>
                  <th className="text-right">回撤</th>
                  <th className="text-right">胜率</th>
                </tr>
              </thead>
              <tbody>
                {results.rows.map((row, idx) => (
                  <tr key={idx} className="border-b border-zinc-800/70">
                    <td className="py-2 font-mono text-xs">{JSON.stringify(row.params)}</td>
                    <td className="py-2 text-right text-green-400">{(row.total_return * 100).toFixed(2)}%</td>
                    <td className="py-2 text-right">{row.sharpe_ratio.toFixed(3)}</td>
                    <td className="py-2 text-right text-red-400">{(row.max_drawdown * 100).toFixed(2)}%</td>
                    <td className="py-2 text-right">{(row.win_rate * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {results?.kind === "walkforward" && (
        <div className={cardCls}>
          <div className="flex justify-between items-center mb-3">
            <div>
              <div className="text-sm font-bold">Walk Forward 结果</div>
              <div className="text-xs text-zinc-400">{results.strategyName}</div>
            </div>
            <div className={`text-sm font-bold ${results.wfScore === "PASS" ? "text-green-400" : "text-red-400"}`}>{results.wfScore}</div>
          </div>
          <div className="grid md:grid-cols-3 gap-4 mb-4 text-sm">
            <div>通过率: <span className="text-cyan-400">{results.passRatio?.toFixed(2)}%</span></div>
            <div>平均收益: <span className="text-green-400">{results.avgTotalReturn?.toFixed(2)}%</span></div>
            <div>平均夏普: <span className="text-yellow-400">{results.avgSharpeRatio?.toFixed(3)}</span></div>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-700">
                  <th className="text-left py-2">周期</th>
                  <th className="text-right">测试收益</th>
                  <th className="text-right">夏普</th>
                  <th className="text-right">回撤</th>
                  <th className="text-center">状态</th>
                </tr>
              </thead>
              <tbody>
                {results.rows.map((row, idx) => (
                  <tr key={idx} className="border-b border-zinc-800/70">
                    <td className="py-2">{row.period}</td>
                    <td className={`py-2 text-right ${row.test_return >= 0 ? "text-green-400" : "text-red-400"}`}>{row.test_return.toFixed(2)}%</td>
                    <td className="py-2 text-right">{row.sharpe.toFixed(3)}</td>
                    <td className="py-2 text-right text-red-400">{row.max_drawdown.toFixed(2)}%</td>
                    <td className="py-2 text-center">{row.passed ? "PASS" : "FAIL"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default BacktestEnhanced;
