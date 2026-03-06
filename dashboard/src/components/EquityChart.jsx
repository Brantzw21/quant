import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

const data = [
  { time: "09:00", equity: 100000 },
  { time: "10:00", equity: 101200 },
  { time: "11:00", equity: 100800 },
  { time: "12:00", equity: 103000 },
  { time: "13:00", equity: 104500 },
  { time: "14:00", equity: 106000 },
];

export default function EquityChart() {
  return (
    <div className="bg-zinc-900 p-4 rounded-2xl border border-zinc-800 flex-1">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-zinc-300">Equity Curve</h2>
        <div className="flex gap-2">
          {["1D", "1W", "1M", "ALL"].map((tf) => (
            <button
              key={tf}
              className={`px-2 py-1 text-xs rounded ${
                tf === "1M"
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" stroke="#52525b" fontSize={11} />
          <YAxis stroke="#52525b" fontSize={11} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#18181b",
              border: "1px solid #27272a",
              borderRadius: "8px",
            }}
            labelStyle={{ color: "#a1a1aa" }}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#22c55e"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorEquity)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
