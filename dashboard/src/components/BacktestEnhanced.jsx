import { useState, useEffect } from "react";
import { Play, Pause, RotateCcw, Save, Download, TrendingUp, TrendingDown } from "lucide-react";

const BacktestEnhanced = () => {
  const [config, setConfig] = useState({
    symbol: 'BTCUSDT',
    startDate: '2024-01-01',
    endDate: '2026-03-01',
    initialCapital: 10000,
    commission: 0.1,
    slippage: 0.05,
    strategy: 'rsi'
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await res.json();
      setResults(data);
    } catch (e) {
      console.error('Backtest failed:', e);
    }
    setLoading(false);
  };

  const runOptimization = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backtest/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...config, iterations: 50 })
      });
      const data = await res.json();
      setResults(data);
    } catch (e) {
      console.error('Optimization failed:', e);
    }
    setLoading(false);
  };

  const runWalkForward = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backtest/walkforward', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await res.json();
      setResults(data);
    } catch (e) {
      console.error('Walk-forward failed:', e);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-zinc-400 mb-1">交易品种</label>
          <select 
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.symbol}
            onChange={e => setConfig({...config, symbol: e.target.value})}
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="BNBUSDT">BNB/USDT</option>
          </select>
        </div>
        
        <div>
          <label className="block text-xs text-zinc-400 mb-1">初始资金</label>
          <input 
            type="number"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.initialCapital}
            onChange={e => setConfig({...config, initialCapital: Number(e.target.value)})}
          />
        </div>
        
        <div>
          <label className="block text-xs text-zinc-400 mb-1">策略</label>
          <select 
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.strategy}
            onChange={e => setConfig({...config, strategy: e.target.value})}
          >
            <option value="rsi">RSI 策略</option>
            <option value="ma">均线策略</option>
            <option value="macd">MACD策略</option>
            <option value="boll">布林带策略</option>
          </select>
        </div>
        
        <div>
          <label className="block text-xs text-zinc-400 mb-1">手续费 (%)</label>
          <input 
            type="number"
            step="0.01"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.commission}
            onChange={e => setConfig({...config, commission: Number(e.target.value)})}
          />
        </div>
        
        <div>
          <label className="block text-xs text-zinc-400 mb-1">滑点 (%)</label>
          <input 
            type="number"
            step="0.01"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={config.slippage}
            onChange={e => setConfig({...config, slippage: Number(e.target.value)})}
          />
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2 flex-wrap">
        <button 
          onClick={runBacktest}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm disabled:opacity-50"
        >
          <Play size={16} /> 回测
        </button>
        
        <button 
          onClick={runOptimization}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm disabled:opacity-50"
        >
          <RotateCcw size={16} /> 参数优化
        </button>
        
        <button 
          onClick={runWalkForward}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm disabled:opacity-50"
        >
          <TrendingUp size={16} /> Walk-Forward
        </button>
      </div>

      {/* 结果展示 */}
      {results && (
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-800 rounded-lg p-4">
            <div className="text-xs text-zinc-400">总收益率</div>
            <div className={`text-2xl font-bold ${results.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {results.totalReturn?.toFixed(2)}%
            </div>
          </div>
          
          <div className="bg-zinc-800 rounded-lg p-4">
            <div className="text-xs text-zinc-400">夏普比率</div>
            <div className="text-2xl font-bold text-cyan-400">
              {results.sharpeRatio?.toFixed(2)}
            </div>
          </div>
          
          <div className="bg-zinc-800 rounded-lg p-4">
            <div className="text-xs text-zinc-400">最大回撤</div>
            <div className="text-2xl font-bold text-red-400">
              -{results.maxDrawdown?.toFixed(2)}%
            </div>
          </div>
          
          <div className="bg-zinc-800 rounded-lg p-4">
            <div className="text-xs text-zinc-400">胜率</div>
            <div className="text-2xl font-bold text-yellow-400">
              {results.winRate?.toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {results?.equityCurve && (
        <div className="bg-zinc-800 rounded-lg p-4">
          <div className="text-sm font-bold mb-2">权益曲线</div>
          <div className="h-48 flex items-end gap-1">
            {results.equityCurve.slice(0, 100).map((v, i) => (
              <div 
                key={i}
                className={`flex-1 ${v >= results.equityCurve[0] ? 'bg-green-500' : 'bg-red-500'}`}
                style={{ height: `${Math.abs(v - results.equityCurve[0]) / (Math.max(...results.equityCurve) - Math.min(...results.equityCurve)) * 100}%` }}
              />
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="text-center py-8 text-zinc-400">
          运行中...
        </div>
      )}
    </div>
  );
};

export default BacktestEnhanced;
