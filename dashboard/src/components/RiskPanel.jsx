import { TrendingUp, TrendingDown, Target, PieChart } from "lucide-react";

export default function RiskPanel() {
  const stats = [
    { label: "Sharpe Ratio", value: "1.42", icon: TrendingUp, color: "text-green-400" },
    { label: "Max Drawdown", value: "-12%", icon: TrendingDown, color: "text-red-400" },
    { label: "Win Rate", value: "54%", icon: Target, color: "text-cyan-400" },
    { label: "Exposure", value: "68%", icon: PieChart, color: "text-yellow-400" },
    { label: "Total Trades", value: "156", icon: null, color: "text-zinc-300" },
    { label: "Profit Factor", value: "1.85", icon: null, color: "text-green-400" },
  ];

  return (
    <div className="bg-zinc-900 p-4 rounded-2xl border border-zinc-800 h-full">
      <h2 className="text-sm font-medium text-zinc-300 mb-4">Risk Monitor</h2>

      <div className="space-y-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex items-center justify-between py-2 border-b border-zinc-800/50"
          >
            <div className="flex items-center gap-2">
              {s.icon && <s.icon size={14} className={s.color} />}
              <span className="text-xs text-zinc-500">{s.label}</span>
            </div>
            <span className={`text-sm font-semibold ${s.color}`}>{s.value}</span>
          </div>
        ))}
      </div>

      <div className="mt-6 p-3 bg-zinc-800/50 rounded-lg">
        <div className="text-xs text-zinc-500 mb-2">Risk Score</div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
            <div className="h-full w-3/5 bg-green-500 rounded-full"></div>
          </div>
          <span className="text-sm text-green-400 font-medium">Low</span>
        </div>
      </div>
    </div>
  );
}
