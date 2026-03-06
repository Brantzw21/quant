// 策略管理组件
import React, { useState, useEffect } from 'react';

export default function StrategyManager({ lang = 'zh' }) {
  const [strategies, setStrategies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [params, setParams] = useState({});

  const t = {
    zh: {
      title: '策略管理',
      name: '策略名称',
      params: '参数',
      edit: '编辑',
      backtest: '回测',
      deploy: '部署',
      save: '保存',
      cancel: '取消'
    },
    en: {
      title: 'Strategy Manager',
      name: 'Name',
      params: 'Parameters',
      edit: 'Edit',
      backtest: 'Backtest',
      deploy: 'Deploy',
      save: 'Save',
      cancel: 'Cancel'
    }
  }[lang] || { zh: {} };

  useEffect(() => {
    // 获取策略列表
    fetch('/api/strategies')
      .then(r => r.json())
      .then(data => {
        setStrategies(data || []);
        if (data && data.length > 0) {
          setSelected(data[0]);
          setParams(data[0]?.params || {});
        }
      });
  }, []);

  const handleSave = () => {
    // 保存策略参数
    console.log('Save params:', params);
  };

  return (
    <div className="space-y-4">
      {/* 策略列表 */}
      <div className="bg-zinc-900 rounded-lg p-4">
        <h3 className="text-lg font-medium mb-4">{t.title}</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {strategies.map(s => (
            <button
              key={s.id}
              onClick={() => { setSelected(s); setParams(s.params || {}); }}
              className={`p-3 rounded-lg text-left transition ${
                selected?.id === s.id 
                  ? 'bg-cyan-600 text-white' 
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
              }`}
            >
              <div className="font-medium">{s.name}</div>
              <div className="text-xs opacity-70">{s.type || 'RSI'}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 策略参数编辑 */}
      {selected && (
        <div className="bg-zinc-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-400 mb-3">
            {selected.name} - {t.params}
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(params).map(([key, value]) => (
              <div key={key}>
                <label className="text-xs text-zinc-500 block mb-1">{key}</label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => setParams({...params, [key]: Number(e.target.value)})}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>

          <div className="flex gap-2 mt-4">
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-cyan-600 rounded-lg text-sm hover:bg-cyan-500"
            >
              {t.save}
            </button>
            <button
              onClick={() => setSelected(null)}
              className="px-4 py-2 bg-zinc-700 rounded-lg text-sm"
            >
              {t.cancel}
            </button>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button className="flex-1 py-3 bg-zinc-800 rounded-lg hover:bg-zinc-700">
          {t.backtest}
        </button>
        <button className="flex-1 py-3 bg-green-600 rounded-lg hover:bg-green-500">
          {t.deploy}
        </button>
      </div>
    </div>
  );
}
