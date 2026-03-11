import { useState, useEffect } from "react";
import RiskIndicator from "./components/RiskIndicator";
import TradingViewChart from "./components/TradingViewChart";
import MultiMarketPanel from "./components/MultiMarketPanel";
import SignalPanel from "./components/SignalPanel";
import SystemMonitorPanel from "./components/SystemMonitorPanel";
import BacktestEnhanced from "./components/BacktestEnhanced";
import StrategyManager from "./components/StrategyManager";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ComposedChart, Line, BarChart, Bar, PieChart, Pie, Cell } from "recharts";
import { TrendingUp, TrendingDown, Target, Activity, Shield, Clock, Play, Square, Globe, Zap, Wallet, Briefcase, Plus, Minus, Edit3, Copy, RefreshCw, PlayCircle, Bell } from "lucide-react";

// 确保数据是数组
const ensureArray = (v) => Array.isArray(v) ? v : v ? [v] : [];

const COLORS = ["#22c55e", "#3b82f6", "#f59e0b", "#a855f7", "#ec4899", "#06b6d4"];

const translations = {
  zh: {
    dashboard: "仪表盘", strategies: "策略", backtest: "回测", liveTrade: "实盘", riskCenter: "风控", logs: "日志",
    system: "系统", running: "运行中", equity: "权益", account: "账户", positions: "持仓", orders: "订单",
    balance: "余额", available: "可用", margin: "保证金", unrealized: "未实现盈亏", total: "总计",
    equityCurve: "资产曲线", drawdown: "回撤", returns: "收益", positions_dist: "持仓分布",
    risk_metrics: "风控指标", strategy: "策略", start: "启动", stop: "停止",
    sharpe: "夏普比率", max_drawdown: "最大回撤", win_rate: "胜率", profit_factor: "盈利因子",
    volatility: "波动率", trades: "交易次数", risk_score: "风险评分",
    backtest: "回测", run: "运行", parameters: "参数", results: "结果",
    start_date: "开始日期", end_date: "结束日期", initial_capital: "初始资金", benchmark: "基准",
    strategy_list: "策略列表", add_strategy: "添加策略", edit: "编辑", delete: "删除", clone: "克隆",
    active: "启用", inactive: "停用", returns_dist: "收益分布", monthly: "月度收益",
    trade_log: "交易记录", signal_log: "信号日志", settings: "设置", refresh: "刷新",
    loading: "加载中...", no_data: "暂无数据", buy: "买入", sell: "卖出", hold: "持有",
    price: "价格", quantity: "数量", amount: "金额", time: "时间", status: "状态", type: "类型",
    side: "方向", filled: "已成交", pending: "待成交", cancelled: "已取消", all: "全部",
    unrealized_pnl: "未实现盈亏", realized_pnl: "已实现盈亏", total_pnl: "总盈亏",
    avg_entry: "平均入场", current_price: "当前价", pnl: "盈亏", roi: "收益率",
    signal_history: "信号历史", risk_state: "风控状态", monthly_returns: "月度收益",
    long: "做多", short: "做空", market: "市价", limit: "限价",
    wallets: "钱包", simulate: "模拟盘", real: "实盘", spot: "现货", futures: "合约",
    asset: "资产", free: "可用", locked: "冻结", position_amount: "持仓量", entry_price: "开仓价",
  },
  en: {
    dashboard: "Dashboard", strategies: "Strategies", backtest: "Backtest", liveTrade: "Live Trade", riskCenter: "Risk Center", logs: "Logs",
    system: "System", running: "Running", equity: "Equity", account: "Account", positions: "Positions", orders: "Orders",
    balance: "Balance", available: "Available", margin: "Margin", unrealized: "Unrealized", total: "Total",
    equityCurve: "Equity Curve", drawdown: "Drawdown", returns: "Returns", positions_dist: "Positions",
    risk_metrics: "Risk Metrics", strategy: "Strategy", start: "Start", stop: "Stop",
    sharpe: "Sharpe", max_drawdown: "Max DD", win_rate: "Win Rate", profit_factor: "Profit Factor",
    volatility: "Volatility", trades: "Trades", risk_score: "Risk Score",
    backtest: "Backtest", run: "Run", parameters: "Parameters", results: "Results",
    start_date: "Start Date", end_date: "End Date", initial_capital: "Initial Capital", benchmark: "Benchmark",
    strategy_list: "Strategy List", add_strategy: "Add Strategy", edit: "Edit", delete: "Delete", clone: "Clone",
    active: "Active", inactive: "Inactive", returns_dist: "Returns Distribution", monthly: "Monthly Returns",
    trade_log: "Trade Log", signal_log: "Signal Log", settings: "Settings", refresh: "Refresh",
    loading: "Loading...", no_data: "No Data", buy: "BUY", sell: "SELL", hold: "HOLD",
    price: "Price", quantity: "Qty", amount: "Amount", time: "Time", status: "Status", type: "Type",
    side: "Side", filled: "Filled", pending: "Pending", cancelled: "Cancelled", all: "All",
    unrealized_pnl: "Unrealized P&L", realized_pnl: "Realized P&L", total_pnl: "Total P&L",
    avg_entry: "Avg Entry", current_price: "Current", pnl: "P&L", roi: "ROI",
    signal_history: "Signal History", risk_state: "Risk State", monthly_returns: "Monthly Returns",
    long: "Long", short: "Short", market: "Market", limit: "Limit",
    wallets: "Wallets", simulate: "Simulate", real: "Real", spot: "Spot", futures: "Futures",
    asset: "Asset", free: "Free", locked: "Locked", position_amount: "Amount", entry_price: "Entry",
  }
};

// Components
const Card = ({ children, className = "" }) => <div className={`bg-zinc-900/80 backdrop-blur border border-zinc-800 rounded-2xl ${className}`}>{children}</div>;
const CardHeader = ({ children }) => <div className="px-4 py-3 border-b border-zinc-800/50">{children}</div>;
const CardTitle = ({ children }) => <h3 className="text-sm font-semibold text-zinc-300">{children}</h3>;
const CardContent = ({ children, className = "" }) => <div className={`p-4 ${className}`}>{children}</div>;

const Button = ({ children, onClick, variant = "default", className = "", disabled = false, icon: Icon }) => {
  const base = "rounded-lg font-medium transition flex items-center justify-center gap-1";
  const variants = { default: "bg-zinc-700 hover:bg-zinc-600 text-white", primary: "bg-cyan-600 hover:bg-cyan-500 text-white", success: "bg-green-600 hover:bg-green-500 text-white", danger: "bg-red-600 hover:bg-red-500 text-white", ghost: "bg-transparent hover:bg-zinc-800 text-zinc-400" };
  return <button onClick={onClick} disabled={disabled} className={`${base} px-3 py-2 text-sm ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>{Icon && <Icon size={16} />}{children}</button>;
};

const Badge = ({ children, variant = "default" }) => {
  const variants = { default: "bg-zinc-700 text-zinc-300", success: "bg-green-900/50 text-green-400", danger: "bg-red-900/50 text-red-400", warning: "bg-yellow-900/50 text-yellow-400", info: "bg-blue-900/50 text-blue-400" };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}>{children}</span>;
};

const StatCard = ({ label, value, trend, icon: Icon, color = "cyan", sub }) => {
  const colors = { cyan: "text-cyan-400", green: "text-green-400", red: "text-red-400", yellow: "text-yellow-400", blue: "text-blue-400" };
  return (
    <Card className="p-4">
      <div className="flex justify-between items-start">
        <div><p className="text-xs text-zinc-500 mb-1">{label}</p><p className={`text-xl font-bold ${colors[color]}`}>{value}</p>{sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}</div>
        {Icon && <Icon size={20} className={colors[color]} />}
      </div>
      {trend !== undefined && <div className={`text-xs mt-2 ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>{trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%</div>}
    </Card>
  );
};

// Dashboard Page
function DashboardPage({ lang, currentAccount, onAccountChange }) {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [account, setAccount] = useState({ equity: 0, balance: 0, available: 0, margin: 0, position: 0, unrealized_pnl: 0, realized_pnl: 0, total_pnl: 0, pnl_percent: 0 });
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [trades, setTrades] = useState([]);
  const [equityData, setEquityData] = useState([]);
  const [performance, setPerformance] = useState({});
  const [logs, setLogs] = useState([]);
  const [signal, setSignal] = useState({});
  const [risk, setRisk] = useState({});
  const [signals, setSignals] = useState([]);
  const [drawdownData, setDrawdownData] = useState([]);
  const [returnsDist, setReturnsDist] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [period, setPeriod] = useState("ALL");
  const [currentStrategy, setCurrentStrategy] = useState(null);

  const fetchData = () => {
    setLoading(true);
    const accountType = currentAccount || 'simulate';
    Promise.all([
      fetch(`/api/account?type=${accountType}`).then(r => r.json()),
      fetch(`/api/positions?type=${accountType}`).then(r => r.json()),
      fetch('/api/orders').then(r => r.json()),
      fetch('/api/trades').then(r => r.json()),
      fetch('/api/equity').then(r => r.json()),
      fetch('/api/performance').then(r => r.json()),
      fetch('/api/logs').then(r => r.json()),
      fetch('/api/strategy').then(r => r.json()),
      fetch('/api/risk').then(r => r.json()),
      fetch('/api/drawdown_history').then(r => r.json()),
      fetch('/api/returns_dist').then(r => r.json()),
      fetch('/api/monthly').then(r => r.json()),
      fetch('/api/strategies').then(r => r.json()),
    ]).then(([acc, pos, ord, trd, eq, perf, lg, sig, rs, dd, rd, mon, strats]) => {
      setAccount(acc || {});
      setPositions(ensureArray(pos));
      setOrders(ensureArray(ord));
      setTrades(ensureArray(trd));
      setEquityData(ensureArray(eq));
      setPerformance(perf || {});
      setLogs(ensureArray(lg));
      setSignal(sig || {});
      setRisk(rs || {});
      setDrawdownData(ensureArray(dd));
      setReturnsDist(ensureArray(rd));
      setMonthlyData(ensureArray(mon));
      setStrategies(ensureArray(strats));
      if (strats?.length > 0 && !currentStrategy) setCurrentStrategy(strats[0]);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  // 根据账户类型获取数据
  useEffect(() => { 
    fetchData(); 
    const timer = setInterval(fetchData, 10000); 
    return () => clearInterval(timer); 
  }, [currentAccount]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold">{t.dashboard}</h2>
          {/* 账户切换 */}
          <select 
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            value={currentAccount}
            onChange={e => onAccountChange(e.target.value)}
          >
            <option value="binance_simulate">🎮 币安模拟盘</option>
            <option value="binance_real">📈 币安实盘</option>
            <option value="a_stock_simulate">🇨🇳 A股模拟盘</option>
            <option value="us_stock_simulate">🇺🇸 美股模拟盘</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          {strategies.length > 0 && (
            <select 
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              value={currentStrategy?.id || ''}
              onChange={e => setCurrentStrategy(strategies.find(s => s.id === Number(e.target.value)))}
            >
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          <Button icon={RefreshCw} onClick={fetchData} disabled={loading}>刷新</Button>
        </div>
      </div>

      {/* 当前信号 */}
      {signal.signal && (
        <Card className="bg-gradient-to-r from-cyan-900/30 to-blue-900/30 border-cyan-800">
          <CardContent className="flex justify-between items-center">
            <div>
              <span className="text-xs text-zinc-400">当前信号: </span>
              <Badge variant={signal.signal === "BUY" ? "success" : signal.signal === "SELL" ? "danger" : "warning"}>
                {signal.signal}
              </Badge>
              <span className="text-xs text-zinc-500 ml-2">{signal.reason}</span>
            </div>
            <div className="text-xs text-zinc-500">
              置信度: {(signal.confidence * 100).toFixed(0)}%
            </div>
          </CardContent>
        </Card>
      )}

      {/* 账户统计 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label={t.equity} value={`$${account.equity?.toLocaleString() || 0}`} trend={account.pnl_percent} icon={Wallet} color="cyan" />
        <StatCard label={t.balance} value={`$${account.balance?.toLocaleString() || 0}`} icon={Briefcase} color="blue" />
        <StatCard label={t.available} value={`$${account.available?.toLocaleString() || 0}`} icon={Activity} color="green" />
        <StatCard label={t.margin} value={`$${account.margin?.toLocaleString() || 0}`} icon={Shield} color="yellow" />
        <StatCard label={t.unrealized_pnl} value={`$${(account.unrealized_pnl || 0).toFixed(2)}`} color={account.unrealized_pnl >= 0 ? "green" : "red"} />
        <StatCard label={t.realized_pnl} value={`$${(account.realized_pnl || 0).toFixed(2)}`} color={account.realized_pnl >= 0 ? "green" : "red"} />
      </div>

      {/* 资产曲线 + 时间周期 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.equityCurve}</CardTitle>
          <div className="flex gap-1">
            {["1D", "1W", "1M", "3M", "ALL"].map(p => (
              <button key={p} onClick={() => setPeriod(p)} className={`px-2 py-1 text-xs rounded ${period === p ? 'bg-cyan-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}>{p}</button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={equityData}>
              <defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/><stop offset="95%" stopColor="#22c55e" stopOpacity={0}/></linearGradient></defs>
              <XAxis dataKey="day" stroke="#52525b" fontSize={11} /><YAxis stroke="#52525b" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={v => [`$${Number(v).toLocaleString()}`, 'Equity']} />
              <Area type="monotone" dataKey="equity" stroke="#22c55e" strokeWidth={2} fill="url(#eqGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 回撤图表 & 收益分布 */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{t.drawdown}</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={150}>
              <AreaChart data={drawdownData}>
                <defs><linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/><stop offset="95%" stopColor="#ef4444" stopOpacity={0}/></linearGradient></defs>
                <XAxis dataKey="date" stroke="#52525b" fontSize={10} />
                <YAxis stroke="#52525b" fontSize={10} domain={['dataMin - 5', 0]} />
                <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={v => [`${v}%`, 'DD']} />
                <Area type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={2} fill="url(#ddGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{t.returns_dist || '收益分布'}</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={returnsDist}>
                <XAxis dataKey="range" stroke="#52525b" fontSize={10} />
                <YAxis stroke="#52525b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 月度收益热力图 */}
      <Card>
        <CardHeader><CardTitle>{t.monthly || '月度收益'}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {(monthlyData || []).map((m, i) => (
              <div key={i} className={`p-2 rounded-lg text-center ${m.is_positive ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                <div className="text-xs text-zinc-500">{m.month}</div>
                <div className={`text-sm font-bold ${m.return >= 0 ? 'text-green-400' : 'text-red-400'}`}>{m.return > 0 ? '+' : ''}{m.return}%</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 持仓 & 订单 */}
      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>{t.positions}</CardTitle></CardHeader>
          <CardContent className="p-0">
            {positions.length > 0 ? (
              <table className="w-full text-sm">
                <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2 px-4">{t.positions}</th><th className="text-left">{t.side}</th><th className="text-right">{t.quantity}</th><th className="text-right">{t.avg_entry}</th><th className="text-right">{t.current_price}</th><th className="text-right">{t.pnl}</th></tr></thead>
                <tbody>
                  {positions.map((p, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 px-4 font-medium">{p.symbol}</td>
                      <td className="py-2"><Badge variant={(p.side || 'long').toLowerCase() === "long" ? "success" : "danger"}>{(p.side || 'LONG').toUpperCase()}</Badge></td>
                      <td className="py-2 text-right">{p.position || p.qty || 0}</td>
                      <td className="py-2 text-right">${p.entry_price || p.entryPrice || 0}</td>
                      <td className="py-2 text-right">${p.current_price || p.currentPrice || 0}</td>
                      <td className={`py-2 text-right ${(p.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>${p.pnl?.toFixed(2) || 0} ({(p.pnl_percent || p.pnlPercent || 0).toFixed(2)}%)</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-zinc-500">{t.no_data}</div>
            )}
          </CardContent>
        </Card>

        {/* 持仓分布饼图 */}
        <Card>
          <CardHeader><CardTitle>{t.positions_dist}</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={positions.map((p, i) => ({ name: p.symbol, value: (p.position || p.qty || 0) * (p.current_price || p.currentPrice || 0), color: COLORS[i % COLORS.length] }))} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" nameKey="name">
                  {positions.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={v => `$${v?.toLocaleString()}`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-2 mt-2">
              {positions.map((p, i) => (
                <div key={i} className="flex items-center gap-1 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{backgroundColor: COLORS[i % COLORS.length]}}></span>
                  <span className="text-zinc-400">{p.symbol}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 绩效指标 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label={t.sharpe} value={performance.sharpe_ratio || "---"} icon={Target} color="cyan" />
        <StatCard label={t.max_drawdown} value={`${performance.max_drawdown || 0}%`} icon={TrendingDown} color="red" />
        <StatCard label={t.win_rate} value={`${performance.win_rate || 0}%`} icon={Zap} color="green" />
        <StatCard label={t.profit_factor} value={performance.profit_factor || "---"} icon={Activity} color="blue" />
        <StatCard label={t.volatility} value={`${performance.volatility || 0}%`} icon={Shield} color="yellow" />
        <StatCard label={t.trades} value={performance.total_trades || 0} icon={Clock} color="blue" />
      </div>

      {/* 交易历史 & 信号日志 */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{t.trade_log}</CardTitle></CardHeader>
          <CardContent className="p-0 max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-zinc-500 border-b border-zinc-800 sticky top-0 bg-zinc-900"><th className="text-left py-2 px-4">{t.time}</th><th className="text-left">{t.signal}</th><th className="text-right">{t.price}</th><th className="text-right">{t.quantity}</th><th className="text-right">{t.status}</th></tr></thead>
              <tbody>
                {trades.slice(0, 15).map((tr, i) => (
                  <tr key={i} className="border-b border-zinc-800/50">
                    <td className="py-1 px-4 text-zinc-400">{tr.time?.slice(11, 19)}</td>
                    <td className={`py-1 ${tr.signal === "BUY" ? "text-green-400" : tr.signal === "SELL" ? "text-red-400" : "text-yellow-400"}`}>{tr.signal}</td>
                    <td className="py-1 text-right">${tr.result?.entry_price?.toLocaleString() || "---"}</td>
                    <td className="py-1 text-right">{tr.result?.qty || tr.result?.quantity || "---"}</td>
                    <td className="py-1 text-right"><Badge variant={tr.result?.status === "success" ? "success" : "warning"}>{tr.result?.status || "---"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="bg-black">
          <CardHeader><CardTitle>{t.signal_history}</CardTitle></CardHeader>
          <CardContent className="p-0 max-h-64 overflow-auto font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-3 py-1 px-4 hover:bg-zinc-900/50">
                <span className="text-zinc-600 shrink-0">{log.time}</span>
                <span className={log.color}>{log.level}</span>
                <span className="text-zinc-300">{log.msg}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Strategies Page
function StrategiesPage({ lang }) {
  const t = translations[lang];
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">{t.strategy_list}</h2>
      </div>
      <StrategyManager />
    </div>
  );
}

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">{t.strategy_list}</h2>
        <Button variant="primary" icon={Plus}>{t.add_strategy}</Button>
      </div>
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {localStrategies.map(s => (
          <Card key={s.id} className="hover:border-zinc-700 transition">
            <CardHeader className="flex justify-between items-start">
              <div><CardTitle className="text-base">{s.name}</CardTitle><p className="text-xs text-zinc-500 mt-1">{s.type} • {s.trades} {t.trades}</p></div>
              <Badge variant={s.status === "active" ? "success" : "default"}>{s.status === "active" ? t.active : t.inactive}</Badge>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="text-center p-2 bg-zinc-800/50 rounded-lg"><p className="text-xs text-zinc-500">{t.returns}</p><p className={`text-sm font-bold ${s.returns >= 0 ? 'text-green-400' : 'text-red-400'}`}>{s.returns > 0 ? '+' : ''}{s.returns}%</p></div>
                <div className="text-center p-2 bg-zinc-800/50 rounded-lg"><p className="text-xs text-zinc-500">{t.sharpe}</p><p className="text-sm font-bold">{s.sharpe}</p></div>
                <div className="text-center p-2 bg-zinc-800/50 rounded-lg"><p className="text-xs text-zinc-500">{t.max_drawdown}</p><p className="text-sm font-bold text-red-400">{s.maxDD}%</p></div>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" icon={Edit3} className="flex-1">{t.edit}</Button>
                <Button variant="ghost" size="sm" icon={Copy} className="flex-1">{t.clone}</Button>
                <Button variant={s.status === "active" ? "danger" : "success"} size="sm" icon={s.status === "active" ? Square : Play} className="flex-1">{s.status === "active" ? t.stop : t.start}</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// Monitor Page (V7: 系统监控 + 多实例)
function MonitorPage({ lang }) {
  const t = translations[lang];
  const [metrics, setMetrics] = useState({});
  const [instances, setInstances] = useState([]);
  const [health, setHealth] = useState({});

  useEffect(() => {
    const fetchData = () => {
      Promise.all([
        fetch('/api/metrics').then(r => r.json()),
        fetch('/api/instances').then(r => r.json()),
        fetch('/api/health').then(r => r.json()),
      ]).then(([m, i, h]) => {
        setMetrics(m);
        setInstances(i);
        setHealth(h);
      });
    };
    fetchData();
    const timer = setInterval(fetchData, 5000);
    return () => clearInterval(timer);
  }, []);

  const riskLightColor = (level) => {
    if (level === "Low" || level === "GREEN") return "bg-green-500";
    if (level === "Medium" || level === "YELLOW") return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">系统监控</h2>
        <Badge variant={health.status === "healthy" ? "success" : "danger"}>{health.status || "unknown"}</Badge>
      </div>

      {/* 系统指标 */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="text-center">
            <div className="text-xs text-zinc-500">CPU</div>
            <div className={`text-2xl font-bold ${(metrics.system?.cpu_percent || 0) > 80 ? 'text-red-400' : 'text-cyan-400'}`}>
              {metrics.system?.cpu_percent || 0}%
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <div className="text-xs text-zinc-500">内存</div>
            <div className={`text-2xl font-bold ${(metrics.system?.memory_percent || 0) > 80 ? 'text-red-400' : 'text-cyan-400'}`}>
              {metrics.system?.memory_percent || 0}%
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <div className="text-xs text-zinc-500">磁盘</div>
            <div className="text-2xl font-bold text-cyan-400">{metrics.system?.disk_percent || 0}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <div className="text-xs text-zinc-500">运行时间</div>
            <div className="text-lg font-bold text-white">{health.uptime_start ? new Date().getTime() - new Date(health.uptime_start).getTime() > 0 ? Math.floor((new Date().getTime() - new Date(health.uptime_start).getTime()) / 1000 / 60) + 'm' : '-' : '-'}</div>
          </CardContent>
        </Card>
      </div>

      {/* 多实例运行面板 */}
      <Card>
        <CardHeader><CardTitle>运行实例</CardTitle></CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead><tr className="text-zinc-500 border-b border-zinc-800">
              <th className="text-left py-2 px-4">状态</th>
              <th className="text-right">权益</th>
              <th className="text-right">回撤</th>
              <th className="text-center">风险灯</th>
              <th className="text-left">策略</th>
              <th className="text-left">信号</th>
              <th className="text-right">心跳</th>
            </tr></thead>
            <tbody>
              {instances.map((inst, i) => (
                <tr key={i} className="border-b border-zinc-800/50">
                  <td className="py-2 px-4">
                    <Badge variant={inst.status === "running" ? "success" : "danger"}>
                      {inst.status === "running" ? "🟢 运行中" : "🔴 停止"}
                    </Badge>
                  </td>
                  <td className="py-2 text-right font-mono">${inst.equity?.toLocaleString()}</td>
                  <td className="py-2 text-right text-red-400">{inst.drawdown}%</td>
                  <td className="py-2 text-center">
                    <span className={`inline-block w-3 h-3 rounded-full ${riskLightColor(inst.risk_light)}`}></span>
                  </td>
                  <td className="py-2">{inst.strategy}</td>
                  <td className="py-2">
                    <Badge variant={inst.signal === "BUY" ? "success" : inst.signal === "SELL" ? "danger" : "warning"}>
                      {inst.signal}
                    </Badge>
                  </td>
                  <td className="py-2 text-right text-zinc-500 text-xs">{inst.last_heartbeat?.slice(11, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* 交易指标 */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>今日交易</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{metrics.trading?.today_trades || 0}</div>
            <div className="text-xs text-zinc-500">成交量 ${metrics.trading?.today_volume?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>风控状态</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <span className={`w-4 h-4 rounded-full ${riskLightColor(metrics.risk?.risk_level)}`}></span>
              <span className="text-xl font-bold">{metrics.risk?.risk_level || "Unknown"}</span>
            </div>
            <div className="text-xs text-zinc-500 mt-1">风险评分: {metrics.risk?.risk_score || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>风险指标</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm"><span className="text-zinc-500">实时回撤</span><span className="text-red-400">{metrics.risk?.real_time_drawdown || 0}%</span></div>
            <div className="flex justify-between text-sm"><span className="text-zinc-500">仓位暴露</span><span className="text-yellow-400">{metrics.risk?.position_exposure || 0}%</span></div>
            <div className="flex justify-between text-sm"><span className="text-zinc-500">连亏次数</span><span className="text-white">{metrics.risk?.consecutive_losses || 0}</span></div>
          </CardContent>
        </Card>
      </div>

      {/* 多市场监控 */}
      <div className="grid md:grid-cols-2 gap-4">
        <MultiMarketPanel />
        <SignalPanel />
      </div>

      {/* 系统监控面板 */}
      <SystemMonitorPanel />
    </div>
  );
}

// Risk Center Page
function RiskCenterPage({ lang }) {
  const t = translations[lang];
  const [risk, setRisk] = useState({});
  const [signals, setSignals] = useState([]);
  
  useEffect(() => { fetch('/api/risk').then(r => r.json()).then(setRisk); }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center"><h2 className="text-xl font-bold">{t.riskCenter}</h2></div>
      
      <Card>
        <CardHeader><CardTitle>{t.riskScore}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="text-4xl font-bold text-cyan-400">{risk.current_risk_score || 0}</div>
            <div className="flex-1">
              <div className="h-3 bg-zinc-700 rounded-full overflow-hidden">
                <div className={`h-full ${risk.current_risk_score < 40 ? 'bg-green-500' : risk.current_risk_score < 70 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{width: `${risk.current_risk_score || 0}%`}}></div>
              </div>
            </div>
            <Badge variant={risk.risk_level === "Low" ? "success" : risk.risk_level === "Medium" ? "warning" : "danger"}>{risk.risk_level}</Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card><CardContent className="text-center">
          <Shield size={24} className="mx-auto mb-2 text-red-400" />
          <div className="text-xs text-zinc-500">止损线</div>
          <div className="text-xl font-bold text-red-400">-{risk.stop_loss_pct || 0}%</div>
        </CardContent></Card>
        <Card><CardContent className="text-center">
          <TrendingUp size={24} className="mx-auto mb-2 text-green-400" />
          <div className="text-xs text-zinc-500">止盈线</div>
          <div className="text-xl font-bold text-green-400">+{risk.take_profit_pct || 0}%</div>
        </CardContent></Card>
        <Card><CardContent className="text-center">
          <Activity size={24} className="mx-auto mb-2 text-blue-400" />
          <div className="text-xs text-zinc-500">仓位限制</div>
          <div className="text-xl font-bold text-blue-400">{risk.max_position_pct || 0}%</div>
        </CardContent></Card>
        <Card><CardContent className="text-center">
          <Zap size={24} className={`mx-auto mb-2 ${risk.circuit_breaker ? 'text-green-400' : 'text-red-400'}`} />
          <div className="text-xs text-zinc-500">熔断</div>
          <Badge variant={risk.circuit_breaker ? "success" : "danger"}>{risk.circuit_breaker ? "ON" : "OFF"}</Badge>
        </CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>{t.riskMetrics}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-zinc-500">VaR (95%)</span><span className="text-red-400">{risk.var_95}%</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">CVaR (95%)</span><span className="text-red-400">{risk.cvar_95}%</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">Exposure</span><span className="text-yellow-400">{risk.exposure}%</span></div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-zinc-500">持仓</span><span className="text-white">{risk.position_size}</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">杠杆</span><span className="text-white">{risk.leverage}x</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">今日交易</span><span className="text-white">{risk.trades_today}</span></div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-zinc-500">最大回撤</span><span className="text-red-400">{risk.max_drawdown}%</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">日损失限制</span><span className="text-red-400">-{risk.daily_loss_limit}%</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">风险等级</span><Badge variant={risk.risk_level === "Low" ? "success" : risk.risk_level === "Medium" ? "warning" : "danger"}>{risk.risk_level}</Badge></div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// 钱包页面
function WalletsPage({ lang }) {
  const t = translations[lang];
  const [accountType, setAccountType] = useState("simulate");
  const [wallets, setWallets] = useState({ spot: [], futures: [], positions: [] });
  const [loading, setLoading] = useState(false);

  const fetchWallets = () => {
    setLoading(true);
    fetch(`/api/wallets?type=${accountType}`)
      .then(r => r.json())
      .then(data => {
        setWallets(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchWallets(); }, [accountType]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">{t.wallets}</h2>
        <div className="flex gap-2">
          <button onClick={() => setAccountType("simulate")} className={`px-4 py-2 rounded-lg text-sm ${accountType === "simulate" ? "bg-cyan-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            {t.simulate}
          </button>
          <button onClick={() => setAccountType("real")} className={`px-4 py-2 rounded-lg text-sm ${accountType === "real" ? "bg-cyan-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            {t.real}
          </button>
          <Button icon={RefreshCw} onClick={fetchWallets} disabled={loading}>刷新</Button>
        </div>
      </div>

      {/* 现货钱包 */}
      {wallets.spot && wallets.spot.length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t.spot} {t.wallets}</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2">{t.asset}</th><th className="text-right py-2">{t.free}</th><th className="text-right py-2">{t.locked}</th><th className="text-right py-2">{t.total}</th></tr></thead>
                <tbody>
                  {wallets.spot.map((item, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 font-medium">{item.asset}</td>
                      <td className="text-right">{item.free?.toFixed(6)}</td>
                      <td className="text-right">{item.locked?.toFixed(6)}</td>
                      <td className="text-right text-cyan-400">{item.total?.toFixed(6)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 合约钱包 */}
      {wallets.futures && wallets.futures.length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t.futures} {t.wallets}</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2">{t.asset}</th><th className="text-right py-2">{t.balance}</th></tr></thead>
                <tbody>
                  {wallets.futures.map((item, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 font-medium">{item.asset}</td>
                      <td className="text-right text-cyan-400">{item.balance?.toFixed(6)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 合约持仓 */}
      {wallets.positions && wallets.positions.length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t.futures} {t.positions}</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2">Symbol</th><th className="text-right py-2">{t.quantity}</th><th className="text-right py-2">{t.entry_price}</th><th className="text-right py-2">{t.pnl}</th><th className="text-right py-2">Leverage</th></tr></thead>
                <tbody>
                  {wallets.positions.map((item, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 font-medium">{item.symbol}</td>
                      <td className="text-right">{item.amount}</td>
                      <td className="text-right">{item.entryPrice}</td>
                      <td className={`text-right ${item.unrealizedPnl >= 0 ? "text-green-400" : "text-red-400"}`}>{item.unrealizedPnl?.toFixed(2)}</td>
                      <td className="text-right">{item.leverage}x</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {(!wallets.spot?.length && !wallets.futures?.length && !wallets.positions?.length) && (
        <div className="text-center text-zinc-500 py-8">{t.no_data}</div>
      )}
      {/* 策略风险监控 */}
      <Card>
        <CardHeader><CardTitle>策略风险</CardTitle></CardHeader>
        <CardContent>
          <RiskIndicator 
            level={risk.risk_level === "Low" ? "low" : risk.risk_level === "Medium" ? "medium" : "high"}
            maxDrawdown={risk.max_drawdown || 0}
            leverage={risk.leverage || 1}
            signals={signals}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// Backtest Page (V10 完整版)
function BacktestPage({ lang }) {
  const t = translations[lang];
  
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">{t.backtest}</h2>
      <BacktestEnhanced />
    </div>
  );
}

  // 市场选项
  const marketOptions = {
    crypto: [
      { code: "BTCUSDT", name: "BTC 比特币" },
      { code: "ETHUSDT", name: "ETH 以太坊" },
      { code: "BNBUSDT", name: "BNB 币安币" }
    ],
    us_stock: [
      { code: "SPX", name: "SPX 标普500" },
      { code: "SPY", name: "SPY ETF" },
      { code: "AAPL", name: "AAPL 苹果" },
      { code: "MSFT", name: "MSFT 微软" },
      { code: "NVDA", name: "NVDA 英伟达" }
    ],
    a_stock: [
      { code: "sz.399006", name: "创业板指" },
      { code: "sh.000300", name: "沪深300" },
      { code: "sh.000016", name: "上证50" }
    ]
  };

  // 当前市场的标的列表
  const currentSymbols = marketOptions[params.market] || marketOptions.crypto;

  // 获取策略列表和守门员规则
  useEffect(() => {
    fetch('/api/strategies').then(r => r.json()).then(data => {
      setStrategyList(data || []);
      if (data && data.length > 0) {
        setParams(p => ({...p, strategy: data[0].name}));
      }
    });
    fetch('/api/backtest/gatekeeper').then(r => r.json()).then(setGatekeeper);
  }, []);

  // 运行回测
  const runBacktest = () => {
    setRunning(true);
    setActiveTab("backtest");
    fetch('/api/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    }).then(r => r.json()).then(data => {
      setResults(data);
      // 获取K线数据
      fetch("/api/enhanced/kline?market=a_stock&symbol=sz.399006")
        .then(r => r.json()).then(kdata => {
          if(kdata && kdata.length > 0) setKlineData(kdata);
        });
      setRunning(false);
    });
  };

  // 运行优化
  const runOptimize = () => {
    setRunning(true);
    setActiveTab("optimize");
    fetch('/api/backtest/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        strategy: params.strategy,
        param_grid: {
          rsi_period: [14, 21, 28],
          oversold: [20, 25, 30],
          overbought: [70, 75, 80]
        }
      })
    }).then(r => r.json()).then(data => {
      setOptimizeResults(data);
      setRunning(false);
    });
  };

  // 运行 Walk Forward
  const runWalkForward = () => {
    setRunning(true);
    setActiveTab("walkforward");
    fetch('/api/backtest/walkforward', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ train_ratio: 0.6, step_ratio: 0.1 })
    }).then(r => r.json()).then(data => {
      setWfResults(data);
      setRunning(false);
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <h2 className="text-xl font-bold">{t.backtest}</h2>
        <div className="flex gap-2">
          <Button variant="primary" icon={PlayCircle} onClick={runBacktest} disabled={running}>
            {running ? <RefreshCw size={14} className="animate-spin mr-1" /> : null} 回测
          </Button>
          <Button variant="default" icon={Target} onClick={runOptimize} disabled={running}>
            参数优化
          </Button>
          <Button variant="default" icon={Activity} onClick={runWalkForward} disabled={running}>
            Walk Forward
          </Button>
        </div>
      </div>

      {/* 参数设置 */}
      <Card>
        <CardHeader><CardTitle>{t.parameters}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div>
              <label className="text-xs text-zinc-500 block mb-1">市场</label>
              <select value={params.market} onChange={(e) => setParams({...params, market: e.target.value, symbol: marketOptions[e.target.value]?.[0]?.code || 'BTCUSDT'})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                <option value="crypto">🚀 加密货币</option>
                <option value="us_stock">🇺🇸 美股</option>
                <option value="a_stock">🇨🇳 A股</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">标的</label>
              <select value={params.symbol} onChange={(e) => setParams({...params, symbol: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                {currentSymbols.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">{t.strategy}</label>
              <select value={params.strategy} onChange={(e) => setParams({...params, strategy: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                {strategyList.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">{t.start_date}</label>
              <input type="date" value={params.start_date} onChange={(e) => setParams({...params, start_date: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-2 text-xs" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">{t.end_date}</label>
              <input type="date" value={params.end_date} onChange={(e) => setParams({...params, end_date: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-2 text-xs" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">{t.initial_capital}</label>
              <input type="number" value={params.initial_capital} onChange={(e) => setParams({...params, initial_capital: Number(e.target.value)})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">手续费(%)</label>
              <input type="number" step="0.01" value={params.fee * 100} onChange={(e) => setParams({...params, fee: Number(e.target.value) / 100})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">滑点(bp)</label>
              <input type="number" value={params.slippage} onChange={(e) => setParams({...params, slippage: Number(e.target.value)})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">随机种子</label>
              <input type="number" value={params.seed || 42} onChange={(e) => setParams({...params, seed: Number(e.target.value)})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 守门员状态 */}
      {gatekeeper && (
        <Card className="bg-gradient-to-r from-amber-900/20 to-orange-900/20 border-amber-800">
          <CardContent className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield size={18} className="text-amber-400" />
                <span className="text-sm text-amber-400">回测守门员</span>
              </div>
              <div className="text-xs text-zinc-400">
                收益率≥{gatekeeper.rules.min_return}% | 回撤≤{gatekeeper.rules.max_drawdown}% | 夏普≥{gatekeeper.rules.min_sharpe}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 回测结果 */}
      {results && activeTab === "backtest" && (
        <>
          {/* 核心指标 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatCard label={t.returns} value={`${results.total_return > 0 ? '+' : ''}${results.total_return}%`} icon={TrendingUp} color={results.total_return >= 0 ? "green" : "red"} />
            <StatCard label={t.sharpe} value={results.stats?.sharpe_ratio || "---"} icon={Target} color="cyan" />
            <StatCard label={t.max_drawdown} value={`${results.stats?.max_drawdown || 0}%`} icon={TrendingDown} color="red" />
            <StatCard label={t.win_rate} value={`${results.stats?.win_rate || 0}%`} icon={Zap} color="green" />
            <StatCard label="盈利因子" value={results.stats?.profit_factor || "---"} icon={Activity} color="blue" />
            <StatCard label="交易次数" value={results.stats?.total_trades || 0} icon={Clock} color="blue" />
          </div>

          {/* VaR/CVaR 风险指标 */}
          {results.risk && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
              <div className="bg-zinc-800/50 rounded-lg p-3 border border-amber-700/50">
                <div className="text-xs text-amber-400 mb-1">VaR (95%)</div>
                <div className="text-lg font-bold text-amber-400">{results.risk.var_95 || 0}%</div>
                <div className="text-xs text-zinc-500">单日最大损失</div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3 border border-red-700/50">
                <div className="text-xs text-red-400 mb-1">CVaR (95%)</div>
                <div className="text-lg font-bold text-red-400">{results.risk.cvar_95 || 0}%</div>
                <div className="text-xs text-zinc-500">极端损失均值</div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3 border border-orange-700/50">
                <div className="text-xs text-orange-400 mb-1">VaR (99%)</div>
                <div className="text-lg font-bold text-orange-400">{results.risk.var_99 || 0}%</div>
                <div className="text-xs text-zinc-500">单日最大损失</div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3 border border-purple-700/50">
                <div className="text-xs text-purple-400 mb-1">CVaR (99%)</div>
                <div className="text-lg font-bold text-purple-400">{results.risk.cvar_99 || 0}%</div>
                <div className="text-xs text-zinc-500">极端损失均值</div>
              </div>
            </div>
          )}

          {/* 收益曲线 */}
          <Card>
            <CardHeader><CardTitle>{t.equityCurve}</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={results.equity_curve}>
                  <defs>
                    <linearGradient id="btEqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#52525b" fontSize={11} />
                  <YAxis stroke="#52525b" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={v => [`$${Number(v).toLocaleString()}`, 'Equity']} />
                  <Area type="monotone" dataKey="equity" stroke="#22c55e" strokeWidth={2} fill="url(#btEqGrad)" name="Equity" />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* 回报率曲线 */}
          {results.returns_curve && (
            <Card className="mt-4">
              <CardHeader><CardTitle>回报率曲线</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={results.returns_curve}>
                    <defs>
                      <linearGradient id="retGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" stroke="#52525b" fontSize={11} />
                    <YAxis yAxisId="left" stroke="#52525b" fontSize={11} unit="%" />
                    <YAxis yAxisId="right" orientation="right" stroke="#52525b" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }} formatter={(v, name) => [name === '标的走势' ? `$${Number(v).toFixed(2)}` : `${Number(v).toFixed(2)}%`, name]} />
                    <Area yAxisId="left" type="monotone" dataKey="cumulative_return" stroke="#3b82f6" strokeWidth={2} fill="url(#retGrad)" name="策略累计回报" />
                    {results.price_data && results.price_data.length > 0 && (
                      <Line yAxisId="right" type="monotone" dataKey={(d, i) => {
                        // 通过 date 匹配 price_data
                        const date = d.date;
                        const priceItem = results.price_data.find(p => p.date === date);
                        return priceItem ? priceItem.close : null;
                      }} stroke="#fbbf24" strokeWidth={1} dot={false} name="标的走势" />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* 优化结果 */}
      {optimizeResults && activeTab === "optimize" && (
        <Card>
          <CardHeader>
            <CardTitle>参数优化结果</CardTitle>
            <span className="text-xs text-zinc-500">共 {optimizeResults.total_combinations} 种组合</span>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead><tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 px-4">参数</th>
                <th className="text-right">收益率</th>
                <th className="text-right">夏普</th>
                <th className="text-right">回撤</th>
                <th className="text-right">胜率</th>
              </tr></thead>
              <tbody>
                {(optimizeResults.all_results || []).slice(0, 10).map((r, i) => (
                  <tr key={i} className={`border-b border-zinc-800/50 ${i === 0 ? 'bg-green-900/20' : ''}`}>
                    <td className="py-2 px-4 font-mono text-xs">
                      {Object.entries(r.params).map(([k, v]) => `${k}:${v}`).join(", ")}
                    </td>
                    <td className={`py-2 text-right ${r.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>{r.total_return}%</td>
                    <td className="py-2 text-right text-cyan-400">{r.sharpe_ratio}</td>
                    <td className="py-2 text-right text-red-400">{r.max_drawdown}%</td>
                    <td className="py-2 text-right">{r.win_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Walk Forward 结果 */}
      {wfResults && activeTab === "walkforward" && (
        <Card>
          <CardHeader>
            <CardTitle>Walk Forward 分析</CardTitle>
            <Badge variant={wfResults.wf_score === "PASS" ? "success" : "danger"}>
              {wfResults.wf_score} (通过率: {wfResults.pass_ratio}%)
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead><tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 px-4">周期</th>
                <th className="text-right">训练收益</th>
                <th className="text-right">测试收益</th>
                <th className="text-right">夏普</th>
                <th className="text-center">状态</th>
              </tr></thead>
              <tbody>
                {(wfResults.periods || []).map((p, i) => (
                  <tr key={i} className="border-b border-zinc-800/50">
                    <td className="py-2 px-4">{p.period}</td>
                    <td className="py-2 text-right">{p.train_return}%</td>
                    <td className={`py-2 text-right ${p.test_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>{p.test_return}%</td>
                    <td className="py-2 text-right text-cyan-400">{p.sharpe}</td>
                    <td className="py-2 text-center">
                      <Badge variant={p.passed ? "success" : "danger"}>{p.passed ? "✓ PASS" : "✗ FAIL"}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Main App
export default function App() {
  const [page, setPage] = useState("Dashboard");
  const [lang, setLang] = useState("zh");
  const [currentAccount, setCurrentAccount] = useState("binance_simulate");
  const [systemStatus, setSystemStatus] = useState({ running: true, price: 67850, signal: "HOLD", market: "BTC/USDT" });
  const t = translations[lang];
  
  // 全局系统状态定时获取
  useEffect(() => {
    const fetchStatus = () => fetch('/api/strategy').then(r => r.json()).then(d => {
      setSystemStatus(s => ({ ...s, running: d.running, signal: d.signal, position: d.position }));
    }).catch(() => {});
    fetchStatus();
    const timer = setInterval(fetchStatus, 5000);
    return () => clearInterval(timer);
  }, []);
  
  const navItems = [
    { id: "Dashboard", icon: TrendingUp, label: t.dashboard },
    { id: "Wallets", icon: Wallet, label: t.wallets },
    { id: "Monitor", icon: Activity, label: "监控" },
    { id: "Strategies", icon: Target, label: t.strategies },
    { id: "Backtest", icon: PlayCircle, label: t.backtest },
    { id: "Risk Center", icon: Shield, label: t.riskCenter },
  ];

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-200">
      {/* 桌面端侧边导航 */}
      <div className="w-60 bg-zinc-900 border-r border-zinc-800 p-4 flex-col hidden md:flex">
        <div className="text-xl font-bold mb-6 text-cyan-400">Quant Pro</div>
        <nav className="space-y-1 flex-1">{navItems.map(item => (
          <div key={item.id} onClick={() => setPage(item.id)} className={`px-3 py-2.5 rounded-xl cursor-pointer text-sm transition flex items-center gap-3 ${page === item.id ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'}`}>
            <item.icon size={18} />{item.label}
          </div>
        ))}</nav>
        <div className="text-xs text-zinc-600 pt-4 border-t border-zinc-800">v2.0.0</div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {/* 顶部栏 */}
        <div className="h-14 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-2 md:px-4 shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            {/* 移动端菜单按钮 */}
            <button className="md:hidden p-2 -ml-2" onClick={() => setPage(p => p === "Menu" ? "Dashboard" : "Menu")}>
              ☰
            </button>
            <span className={`w-2 h-2 rounded-full shrink-0 ${systemStatus?.running ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></span>
            <span className={`text-xs sm:text-sm shrink-0 ${systemStatus?.running ? 'text-green-400' : 'text-red-400'}`}>{systemStatus?.running ? t.running : 'Stopped'}</span>
            <span className="text-xs sm:text-sm text-zinc-500 ml-1 shrink-0 hidden xs:inline">{systemStatus?.market}</span>
            <span className="text-xs sm:text-sm font-mono text-white ml-1 truncate">${systemStatus?.price?.toLocaleString()}</span>
          </div>
          <button onClick={() => setLang(l => l === "zh" ? "en" : "zh")} className="px-2 py-1 text-xs bg-zinc-800 rounded-lg shrink-0 ml-2">{lang === "zh" ? "EN" : "中"}</button>
        </div>
        
        {/* 主内容区 */}
        <div className="flex-1 p-2 md:p-4 overflow-auto pb-20 md:pb-4">
          {page === "Dashboard" && <DashboardPage lang={lang} currentAccount={currentAccount} onAccountChange={setCurrentAccount} />}
          {page === "Wallets" && <WalletsPage lang={lang} />}
          {page === "Monitor" && <MonitorPage lang={lang} />}
          {page === "Strategies" && <StrategiesPage lang={lang} />}
          {page === "Backtest" && <BacktestPage lang={lang} />}
          {page === "Risk Center" && <RiskCenterPage lang={lang} />}
        </div>
      </div>

      {/* 移动端底部导航 */}
      <div className="fixed bottom-0 left-0 right-0 bg-zinc-900 border-t border-zinc-800 flex justify-around py-2 md:hidden z-50">
        {navItems.map(item => (
          <div key={item.id} onClick={() => setPage(item.id)} className={`flex flex-col items-center text-xs ${page === item.id ? "text-cyan-400" : "text-zinc-500"}`}>
            <item.icon size={20} />
            <span className="text-[10px] mt-1">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
