import { useState, useEffect } from "react";
import { RefreshCw, TrendingUp, TrendingDown, Activity, Globe, Wallet } from "lucide-react";

const MultiMarketPanel = () => {
  const [markets, setMarkets] = useState({
    crypto: {},
    astock: {},
    us_stock: {}
  });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/market/all');
      const data = await res.json();
      setMarkets(data.markets || {});
      setLoading(false);
    } catch (e) {
      console.error('Failed to fetch market data:', e);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const renderCrypto = () => {
    const data = markets.crypto || {};
    return Object.entries(data).map(([symbol, info]) => (
      <div key={symbol} className="market-card">
        <div className="market-header">
          <span className="symbol">{symbol}</span>
          <span className={`change ${info.change_24h >= 0 ? 'up' : 'down'}`}>
            {info.change_24h >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {info.change_24h?.toFixed(2)}%
          </span>
        </div>
        <div className="market-price">${info.price?.toLocaleString()}</div>
        <div className="market-info">
          <span>RSI: {info.rsi || '-'}</span>
          <span className={`trend ${info.trend}`}>{info.trend}</span>
        </div>
      </div>
    ));
  };

  const renderAstock = () => {
    const data = markets.astock || {};
    return Object.entries(data).map(([code, info]) => (
      <div key={code} className="market-card">
        <div className="market-header">
          <span className="symbol">{info.name || code}</span>
        </div>
        <div className="market-price">{info.close?.toFixed(2)}</div>
      </div>
    ));
  };

  const renderUsstock = () => {
    const data = markets.us_stock || {};
    return Object.entries(data).map(([symbol, info]) => (
      <div key={symbol} className="market-card">
        <div className="market-header">
          <span className="symbol">{symbol}</span>
          <span className={`change ${info.change >= 0 ? 'up' : 'down'}`}>
            {info.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {info.change?.toFixed(2)}%
          </span>
        </div>
        <div className="market-price">${info.price}</div>
      </div>
    ));
  };

  return (
    <div className="panel multi-market-panel">
      <div className="panel-header">
        <Globe size={18} />
        <span>多市场监控</span>
        <button className="refresh-btn" onClick={fetchData}>
          <RefreshCw size={14} />
        </button>
      </div>
      
      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="panel-content">
          <div className="market-section">
            <h4><Activity size={14} /> 数字货币</h4>
            <div className="market-grid">{renderCrypto()}</div>
          </div>
          
          <div className="market-section">
            <h4><Globe size={14} /> A股</h4>
            <div className="market-grid">{renderAstock()}</div>
          </div>
          
          <div className="market-section">
            <h4><Wallet size={14} /> 美股</h4>
            <div className="market-grid">{renderUsstock()}</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiMarketPanel;
