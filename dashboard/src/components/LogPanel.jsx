export default function LogPanel() {
  const logs = [
    { time: "14:30:25", level: "INFO", msg: "Strategy loaded successfully", color: "text-green-400" },
    { time: "14:30:26", level: "INFO", msg: "Signal generated: BUY RSI(28)", color: "text-blue-400" },
    { time: "14:30:27", level: "INFO", msg: "Order executed: 0.01 BTC @ 67850", color: "text-green-400" },
    { time: "14:35:00", level: "WARN", msg: "High volatility detected: 3.2%", color: "text-yellow-400" },
    { time: "14:40:12", level: "INFO", msg: "Market data updated", color: "text-zinc-400" },
    { time: "14:45:00", level: "INFO", msg: "Risk check passed", color: "text-green-400" },
    { time: "14:50:00", level: "DEBUG", msg: "Position size: 0.02 BTC", color: "text-zinc-500" },
  ];

  return (
    <div className="bg-black text-zinc-300 font-mono text-xs p-4 rounded-2xl border border-zinc-800 h-64 overflow-auto">
      <div className="flex items-center gap-2 mb-3 text-zinc-500">
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
        </div>
        <span className="ml-2">terminal</span>
      </div>
      
      {logs.map((log, i) => (
        <div key={i} className="flex gap-3 py-0.5 hover:bg-zinc-900/50">
          <span className="text-zinc-600 shrink-0">{log.time}</span>
          <span className={log.color}>{log.level}</span>
          <span className="text-zinc-300">{log.msg}</span>
        </div>
      ))}
      
      <div className="flex items-center gap-2 mt-2 text-zinc-500">
        <span className="animate-pulse">▋</span>
        <input
          type="text"
          placeholder="Enter command..."
          className="bg-transparent border-none outline-none text-zinc-400 w-full text-xs"
        />
      </div>
    </div>
  );
}
