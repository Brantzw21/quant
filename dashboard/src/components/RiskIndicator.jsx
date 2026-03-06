// 风险灯组件
import React from 'react';

export default function RiskIndicator({ level = 'low', maxDrawdown = 0, leverage = 1, signals = [] }) {
  const getLevelColor = (lvl) => {
    switch(lvl) {
      case 'low': return 'bg-green-500';
      case 'medium': return 'bg-yellow-500';
      case 'high': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getLevelText = (lvl) => {
    switch(lvl) {
      case 'low': return '低';
      case 'medium': return '中';
      case 'high': return '高';
      default: return '未知';
    }
  };

  // 计算风险等级
  const calcRiskLevel = () => {
    if (maxDrawdown > 15 || leverage > 2) return 'high';
    if (maxDrawdown > 8 || leverage > 1.5) return 'medium';
    return 'low';
  };

  const currentLevel = level || calcRiskLevel();

  return (
    <div className="space-y-4">
      {/* 账户风险 */}
      <div className="bg-zinc-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-zinc-400 mb-3">账户风险</h3>
        
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">风险等级</span>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getLevelColor(currentLevel)}`} />
            <span className="text-sm">{getLevelText(currentLevel)}</span>
          </div>
        </div>

        <div className="flex items-center justify-between mt-2">
          <span className="text-zinc-500">最大回撤</span>
          <span className="text-sm text-red-400">{maxDrawdown?.toFixed(1)}%</span>
        </div>

        <div className="flex items-center justify-between mt-2">
          <span className="text-zinc-500">杠杆</span>
          <span className="text-sm">{leverage?.toFixed(1)}x</span>
        </div>
      </div>

      {/* 策略风险 */}
      {signals && signals.length > 0 && (
        <div className="bg-zinc-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-400 mb-3">策略风险</h3>
          
          {signals.map((s, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <span className="text-sm">{s.name || s.strategy}</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  s.risk === 'high' ? 'bg-red-500' : 
                  s.risk === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                }`} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
