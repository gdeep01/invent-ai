import { useEffect, useState } from 'react';
import { Bell, ChevronRight, Store, TrendingUp, Upload } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import api from '../services/api';

export default function DashboardPage() {
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [mandiPrices, setMandiPrices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInitial();
  }, []);

  useEffect(() => {
    if (selectedStore) {
      loadSummary(selectedStore);
    }
  }, [selectedStore]);

  const loadInitial = async () => {
    try {
      const [storeRows, alertRows, mandiRows] = await Promise.all([
        api.getStores(),
        api.getAlerts(),
        api.getMandiPrices(),
      ]);
      setStores(storeRows);
      setAlerts(alertRows);
      setMandiPrices(Array.isArray(mandiRows) ? mandiRows : mandiRows.records || []);
      if (storeRows.length) {
        setSelectedStore(storeRows[0].store_id);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async (storeId) => {
    try {
      const summaryData = await api.getReorderSummary(storeId);
      setSummary(summaryData);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const dismissAlert = async (alertId) => {
    await api.dismissAlert(alertId);
    setAlerts((current) => current.filter((alert) => alert.id !== alertId));
  };

  if (loading) {
    return <div className="skeleton-grid"><div className="skeleton-card" /><div className="skeleton-card" /><div className="skeleton-card" /></div>;
  }

  if (!stores.length) {
    return (
      <div className="card empty-state">
        <Upload size={52} />
        <h2>No products yet</h2>
        <p>Upload a CSV to build your first InventAI workspace.</p>
        <Link to="/upload" className="btn btn-primary">Upload CSV</Link>
      </div>
    );
  }

  return (
    <div>
      <div className="hero-panel">
        <div>
          <div className="nav-brand"><span className="nav-brand-icon"><Store size={24} /></span>InventAI</div>
          <h1 className="card-title">Inventory intelligence that stays action-ready</h1>
          <p className="card-subtitle">Forecast demand, spot low-stock risk, and track mandi-driven reorder decisions.</p>
        </div>
        <select className="form-select compact-select" value={selectedStore} onChange={(e) => setSelectedStore(e.target.value)}>
          {stores.map((store) => <option key={store.store_id} value={store.store_id}>{store.name}</option>)}
        </select>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{stores.length}</div><div className="stat-label">Stores</div></div>
        <div className="stat-card"><div className="stat-value critical">{summary?.critical || 0}</div><div className="stat-label">Low Stock Items</div></div>
        <div className="stat-card"><div className="stat-value success">{summary ? Math.max(0, 100 - (summary.medium * 2)) : 0}</div><div className="stat-label">Forecast Accuracy (proxy)</div></div>
        <div className="stat-card"><div className="stat-value warning">{alerts.length}</div><div className="stat-label">Active Alerts</div></div>
      </div>

      {!!alerts.length && (
        <div className="alert-stack">
          {alerts.slice(0, 4).map((alert) => (
            <div key={alert.id} className="card notification-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                <div>
                  <div className={`badge badge-${alert.severity === 'critical' ? 'critical' : alert.severity === 'high' ? 'high' : 'medium'}`}>{alert.severity}</div>
                  <p style={{ marginTop: '0.75rem' }}>{alert.message}</p>
                </div>
                <button className="btn btn-ghost" onClick={() => dismissAlert(alert.id)}>Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!alerts.length && (
        <div className="card empty-state" style={{ marginTop: '1.5rem' }}>
          <Bell size={48} />
          <h2>No active alerts</h2>
          <p>Your latest forecasts and reorder checks have not raised any issues.</p>
        </div>
      )}

      <div className="split-grid">
        <Link to="/reorder" className="card feature-card">
          <div className="feature-card-head"><Bell size={20} /><h2>Reorder priorities</h2></div>
          <p>Jump into critical, warning, and okay reorder buckets with clear reasons.</p>
          <span className="feature-link">Open reorder workspace <ChevronRight size={16} /></span>
        </Link>
        <Link to="/forecast" className="card feature-card">
          <div className="feature-card-head"><TrendingUp size={20} /><h2>Forecast with confidence bands</h2></div>
          <p>Compare ARIMA versus baseline projections and watch festival boost impact.</p>
          <span className="feature-link">Open forecast workspace <ChevronRight size={16} /></span>
        </Link>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">Current mandi prices</h2>
            <p className="card-subtitle">Live-ish market context for your reorder decisions.</p>
          </div>
        </div>
        <div className="price-grid">
          {mandiPrices.slice(0, 6).map((price, index) => (
            <div key={`${price.commodity}-${index}`} className="price-card">
              <div className="card-subtitle">{price.commodity}</div>
              <div className="price-value">Rs. {price.modal_price}</div>
              <div className="card-subtitle">{price.market}, {price.state}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
