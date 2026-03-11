import { useState, useEffect } from "react";
import { Cpu, HardDrive, Activity, Server, AlertTriangle } from "lucide-react";

const SystemMonitorPanel = () => {
  const [metrics, setMetrics] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    status: 'ok'
  });
  const [processes, setProcesses] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/system');
      const data = await res.json();
      setMetrics({
        cpu: data.metrics?.cpu_percent || 0,
        memory: data.metrics?.memory_percent || 0,
        disk: data.metrics?.disk_percent || 0,
        status: data.status || 'ok'
      });
      setAlerts(data.alerts || []);
      setLoading(false);
    } catch (e) {
      console.error('Failed to fetch system data:', e);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getMetricColor = (value) => {
    if (value > 80) return '#ef4444';
    if (value > 60) return '#f59e0b';
    return '#22c55e';
  };

  const renderMetric = (icon, label, value) => (
    <div className="metric-item">
      <div className="metric-icon">{icon}</div>
      <div className="metric-info">
        <div className="metric-label">{label}</div>
        <div className="metric-value" style={{ color: getMetricColor(value) }}>
          {value.toFixed(1)}%
        </div>
      </div>
      <div className="metric-bar">
        <div 
          className="metric-fill" 
          style={{ 
            width: `${Math.min(value, 100)}%`,
            backgroundColor: getMetricColor(value)
          }} 
        />
      </div>
    </div>
  );

  return (
    <div className="panel system-monitor-panel">
      <div className="panel-header">
        <Server size={18} />
        <span>系统监控</span>
        <span className={`status-badge ${metrics.status}`}>
          {metrics.status === 'ok' ? '正常' : '告警'}
        </span>
      </div>
      
      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="panel-content">
          <div className="metrics-grid">
            {renderMetric(<Cpu size={20} />, 'CPU', metrics.cpu)}
            {renderMetric(<Activity size={20} />, '内存', metrics.memory)}
            {renderMetric(<HardDrive size={20} />, '磁盘', metrics.disk)}
          </div>
          
          {alerts.length > 0 && (
            <div className="alerts-section">
              <h4><AlertTriangle size={14} /> 告警</h4>
              {alerts.map((alert, i) => (
                <div key={i} className={`alert-item ${alert.level}`}>
                  {alert.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SystemMonitorPanel;
