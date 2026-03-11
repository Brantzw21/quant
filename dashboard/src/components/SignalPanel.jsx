import { useState, useEffect } from "react";
import { Bell, TrendingUp, TrendingDown, Pause } from "lucide-react";

const SignalPanel = () => {
  const [signals, setSignals] = useState({
    crypto: {},
    astock: {},
    us_stock: {}
  });
  const [loading, setLoading] = useState(true);

  const fetchSignals = async () => {
    try {
      const res = await fetch('/api/signals');
      const data = await res.json();
      setSignals(data.markets || {});
      setLoading(false);
    } catch (e) {
      console.error('Failed to fetch signals:', e);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 30000);
    return () => clearInterval(interval);
  }, []);

  const getSignalIcon = (signal) => {
    switch (signal) {
      case 'BUY': return <TrendingUp size={16} className="signal-buy" />;
      case 'SELL': return <TrendingDown size={16} className="signal-sell" />;
      default: return <Pause size={16} className="signal-hold" />;
    }
  };

  const getSignalClass = (signal) => {
    switch (signal) {
      case 'BUY': return 'signal-buy';
      case 'SELL': return 'signal-sell';
      default: return 'signal-hold';
    }
  };

  const renderSignals = (marketSignals) => {
    return Object.entries(marketSignals || {}).map(([symbol, data]) => (
      <div key={symbol} className="signal-row">
        <div className="signal-symbol">{symbol}</div>
        <div className={`signal-value ${getSignalClass(data.signal)}`}>
          {getSignalIcon(data.signal)}
          <span>{data.signal}</span>
        </div>
        <div className="signal-confidence">
          {((data.confidence || 0) * 100).toFixed(0)}%
        </div>
        <div className="signal-price">{data.price?.toFixed(2) || '-'}</div>
      </div>
    ));
  };

  return (
    <div className="panel signal-panel">
      <div className="panel-header">
        <Bell size={18} />
        <span>交易信号</span>
      </div>
      
      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="panel-content">
          <div className="signal-section">
            <h4>数字货币</h4>
            {renderSignals(signals.crypto)}
          </div>
          
          <div className="signal-section">
            <h4>A股</h4>
            {renderSignals(signals.astock)}
          </div>
          
          <div className="signal-section">
            <h4>美股</h4>
            {renderSignals(signals.us_stock)}
          </div>
        </div>
      )}
    </div>
  );
};

export default SignalPanel;
