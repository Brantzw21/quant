export default function Sidebar({ activeTab, onChange, isMobile, isOpen, onToggle }) {
  const items = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "strategies", label: "Strategies", icon: "📈" },
    { id: "backtest", label: "Backtest", icon: "🔄" },
    { id: "live", label: "Live", icon: "⚡" },
    { id: "risk", label: "Risk", icon: "🛡️" },
    { id: "logs", label: "Logs", icon: "📋" },
  ];

  // 移动端使用底部导航
  if (isMobile) {
    return (
      <>
        {/* 移动端顶部栏 */}
        <div className="fixed top-0 left-0 right-0 h-14 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-4 z-50">
          <span className="text-lg font-semibold text-cyan-400">Quant</span>
          <button onClick={onToggle} className="p-2 text-zinc-400">
            {isOpen ? "✕" : "☰"}
          </button>
        </div>
        
        {/* 移动端侧边栏抽屉 */}
        {isOpen && (
          <div className="fixed inset-0 bg-black/50 z-40" onClick={onToggle}>
            <div className="w-60 bg-zinc-900 h-full p-4" onClick={e => e.stopPropagation()}>
              <h1 className="text-xl font-semibold mb-6 text-cyan-400">Quant System</h1>
              <nav className="space-y-1">
                {items.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => { onChange(item.id); onToggle(); }}
                    className={`px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors ${
                      activeTab === item.id 
                        ? "bg-cyan-500/20 text-cyan-400" 
                        : "text-zinc-300 hover:bg-zinc-800"
                    }`}
                  >
                    {item.icon} {item.label}
                  </div>
                ))}
              </nav>
            </div>
          </div>
        )}
        
        {/* 底部导航 */}
        <div className="fixed bottom-0 left-0 right-0 bg-zinc-900 border-t border-zinc-800 flex justify-around py-2 z-30">
          {items.slice(0, 5).map((item) => (
            <div
              key={item.id}
              onClick={() => onChange(item.id)}
              className={`flex flex-col items-center text-xs cursor-pointer ${
                activeTab === item.id ? "text-cyan-400" : "text-zinc-500"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="hide-mobile">{item.label}</span>
            </div>
          ))}
        </div>
      </>
    );
  }

  // 桌面端侧边栏
  return (
    <div className="w-60 bg-zinc-900 p-4 border-r border-zinc-800 flex flex-col">
      <h1 className="text-xl font-semibold mb-6 text-cyan-400">Quant System</h1>

      <nav className="space-y-1 flex-1">
        {items.map((item) => (
          <div
            key={item.id}
            onClick={() => onChange(item.id)}
            className={`px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors ${
              activeTab === item.id 
                ? "bg-cyan-500/20 text-cyan-400" 
                : "text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            {item.icon} {item.label}
          </div>
        ))}
      </nav>
      
      <div className="pt-4 border-t border-zinc-800">
        <div className="text-xs text-zinc-500">v2.0</div>
      </div>
    </div>
  );
}
