import { Activity, Wifi } from "lucide-react";

export default function TopBar() {
  return (
    <div className="h-14 flex items-center justify-between px-6 border-b border-zinc-800 bg-zinc-900">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
          <span className="text-sm text-zinc-400">System:</span>
          <span className="text-sm text-green-400 font-medium">Running</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-500">
          <Activity size={14} />
          <span className="text-xs">BTC/USDT</span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-sm">
          <span className="text-zinc-400">Equity:</span>
          <span className="font-semibold text-white ml-2">$124,532</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-500">
          <Wifi size={14} />
          <span className="text-xs">Connected</span>
        </div>
      </div>
    </div>
  );
}
