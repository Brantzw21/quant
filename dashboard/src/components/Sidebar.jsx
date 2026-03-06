export default function Sidebar() {
  const items = [
    { id: "dashboard", label: "Dashboard" },
    { id: "strategies", label: "Strategies" },
    { id: "backtest", label: "Backtest" },
    { id: "live", label: "Live Trade" },
    { id: "risk", label: "Risk Monitor" },
    { id: "logs", label: "Logs" },
  ];

  return (
    <div className="w-60 bg-zinc-900 p-4 border-r border-zinc-800 flex flex-col">
      <h1 className="text-xl font-semibold mb-6 text-cyan-400">Quant System</h1>

      <nav className="space-y-1 flex-1">
        {items.map((item) => (
          <div
            key={item.id}
            className="px-3 py-2.5 rounded-lg hover:bg-zinc-800 cursor-pointer text-sm text-zinc-300 hover:text-white transition-colors"
          >
            {item.label}
          </div>
        ))}
      </nav>
      
      <div className="pt-4 border-t border-zinc-800">
        <div className="text-xs text-zinc-500">v1.0.0</div>
      </div>
    </div>
  );
}
