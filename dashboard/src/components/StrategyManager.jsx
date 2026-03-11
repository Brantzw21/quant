import { useState, useEffect } from "react";
import { Save, RefreshCw, Play, Settings } from "lucide-react";

const StrategyManager = () => {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [params, setParams] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchStrategies = async () => {
    try {
      const res = await fetch('/api/strategies');
      const data = await res.json();
      setStrategies(data || []);
      
      if (data?.length > 0 && !selectedStrategy) {
        setSelectedStrategy(data[0]);
        setParams(data[0].params || {});
      }
    } catch (e) {
      console.error('Failed to fetch strategies:', e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const saveParams = async () => {
    try {
      await fetch('/api/strategy/params', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategyId: selectedStrategy?.id,
          params: params
        })
      });
      alert('参数已保存');
    } catch (e) {
      console.error('Failed to save params:', e);
    }
  };

  const toggleStrategy = async (strategy) => {
    try {
      await fetch('/api/strategy/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          strategyId: strategy.id,
          enabled: !strategy.enabled 
        })
      });
      fetchStrategies();
    } catch (e) {
      console.error('Failed to toggle strategy:', e);
    }
  };

  // 策略参数配置模板
  const paramTemplates = {
    rsi: [
      { key: 'rsi_period', label: 'RSI周期', type: 'number', min: 5, max: 30 },
      { key: 'rsi_overbought', label: 'RSI超买', type: 'number', min: 60, max: 90 },
      { key: 'rsi_oversold', label: 'RSI超卖', type: 'number', min: 10, max: 40 },
    ],
    ma: [
      { key: 'ma_short', label: '短期均线', type: 'number', min: 5, max: 30 },
      { key: 'ma_long', label: '长期均线', type: 'number', min: 20, max: 100 },
    ],
    macd: [
      { key: 'macd_fast', label: '快线周期', type: 'number', min: 5, max: 20 },
      { key: 'macd_slow', label: '慢线周期', type: 'number', min: 20, max: 50 },
      { key: 'macd_signal', label: '信号线', type: 'number', min: 5, max: 15 },
    ],
    boll: [
      { key: 'boll_period', label: '布林周期', type: 'number', min: 10, max: 30 },
      { key: 'boll_std', label: '标准差倍数', type: 'number', min: 1.5, max: 3 },
    ]
  };

  if (loading) {
    return <div className="text-center py-8 text-zinc-400">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      {/* 策略列表 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {strategies.map(strategy => (
          <div 
            key={strategy.id}
            onClick={() => {
              setSelectedStrategy(strategy);
              setParams(strategy.params || {});
            }}
            className={`p-4 rounded-lg border cursor-pointer transition ${
              selectedStrategy?.id === strategy.id 
                ? 'border-cyan-500 bg-cyan-900/20' 
                : 'border-zinc-700 bg-zinc-800 hover:border-zinc-600'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="font-bold">{strategy.name}</div>
                <div className="text-xs text-zinc-400">{strategy.description || '暂无描述'}</div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleStrategy(strategy);
                }}
                className={`px-2 py-1 text-xs rounded ${
                  strategy.enabled 
                    ? 'bg-green-600 text-white' 
                    : 'bg-zinc-600 text-zinc-300'
                }`}
              >
                {strategy.enabled ? '启用' : '停用'}
              </button>
            </div>
            
            <div className="flex gap-4 text-xs text-zinc-500 mt-2">
              <span>胜率: {strategy.winRate || '-'}</span>
              <span>夏普: {strategy.sharpe || '-'}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 参数配置 */}
      {selectedStrategy && (
        <div className="bg-zinc-800 rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold">参数配置: {selectedStrategy.name}</h3>
            <button 
              onClick={saveParams}
              className="flex items-center gap-2 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-sm"
            >
              <Save size={14} /> 保存
            </button>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(paramTemplates[selectedStrategy.key] || []).map(p => (
              <div key={p.key}>
                <label className="block text-xs text-zinc-400 mb-1">{p.label}</label>
                <input
                  type={p.type}
                  className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm"
                  value={params[p.key] || ''}
                  onChange={e => setParams({...params, [p.key]: Number(e.target.value)})}
                />
              </div>
            ))}
          </div>

          {/* 风控参数 */}
          <div className="mt-4 pt-4 border-t border-zinc-700">
            <h4 className="text-sm font-bold mb-3">风控参数</h4>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs text-zinc-400 mb-1">止损 (%)</label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm"
                  value={params.stop_loss || 3}
                  onChange={e => setParams({...params, stop_loss: Number(e.target.value)})}
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1">止盈 (%)</label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm"
                  value={params.take_profit || 8}
                  onChange={e => setParams({...params, take_profit: Number(e.target.value)})}
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1">仓位比例 (%)</label>
                <input
                  type="number"
                  step="1"
                  className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm"
                  value={params.position_size || 50}
                  onChange={e => setParams({...params, position_size: Number(e.target.value)})}
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1">最大持仓</label>
                <input
                  type="number"
                  className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm"
                  value={params.max_positions || 3}
                  onChange={e => setParams({...params, max_positions: Number(e.target.value)})}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StrategyManager;
