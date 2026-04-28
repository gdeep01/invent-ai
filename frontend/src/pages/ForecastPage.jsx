import { useEffect, useEffectEvent, useMemo, useState } from 'react';
import { Clock3, RefreshCw, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

import api from '../services/api';

export default function ForecastPage() {
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [horizon, setHorizon] = useState(7);
  const [model, setModel] = useState('arima');
  const [forecast, setForecast] = useState(null);
  const [pollingTaskId, setPollingTaskId] = useState('');
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const loadForecast = useEffectEvent(async () => {
    if (!selectedStore) return;
    setLoading(true);
    try {
      const data = await api.getForecast(selectedStore, horizon);
      setForecast(data);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  });

  useEffect(() => {
    api.getStores().then((rows) => {
      setStores(rows);
      if (rows.length) setSelectedStore(rows[0].store_id);
    }).catch((error) => toast.error(error.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedStore) {
      loadForecast();
    }
  }, [selectedStore, horizon]);

  useEffect(() => {
    if (!pollingTaskId) return undefined;
    let isActive = true;
    const intervalId = window.setInterval(async () => {
      try {
        const status = await api.getForecastStatus(pollingTaskId);
        if (!isActive) return;
        if (status.status === 'success') {
          window.clearInterval(intervalId);
          setPollingTaskId('');
          setRunning(false);
          await loadForecast();
          toast.success('Forecast completed');
        }
        if (status.status === 'failure') {
          window.clearInterval(intervalId);
          setPollingTaskId('');
          setRunning(false);
          toast.error(status.error_message || 'Forecast failed');
        }
      } catch (error) {
        window.clearInterval(intervalId);
        setPollingTaskId('');
        setRunning(false);
        toast.error(error.message || 'Unable to refresh forecast status');
      }
    }, 3000);
    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [pollingTaskId, selectedStore, horizon]);

  const startForecast = async () => {
    setRunning(true);
    try {
      const response = await api.runForecast(selectedStore, horizon, null, model);
      setPollingTaskId(response.task_id);
      toast.success('Forecast job queued');
    } catch (error) {
      setRunning(false);
      toast.error(error.message);
    }
  };

  const productSummary = useMemo(() => {
    const grouped = {};
    (forecast?.forecasts || []).forEach((row) => {
      if (!grouped[row.sku_name]) {
        grouped[row.sku_name] = {
          sku_name: row.sku_name,
          total_units: 0,
          days: 0,
          avg_units: 0,
          festival_boost_applied: false,
        };
      }
      grouped[row.sku_name].total_units += row.predicted_units;
      grouped[row.sku_name].days += 1;
      grouped[row.sku_name].festival_boost_applied = grouped[row.sku_name].festival_boost_applied || row.festival_boost_applied;
    });

    return Object.values(grouped)
      .map((item) => ({
        ...item,
        avg_units: item.days ? item.total_units / item.days : 0,
      }))
      .sort((a, b) => b.total_units - a.total_units);
  }, [forecast]);

  const dailyForecastRows = useMemo(() => (
    [...(forecast?.forecasts || [])].sort((a, b) => {
      if (a.forecast_date === b.forecast_date) {
        return b.predicted_units - a.predicted_units;
      }
      return String(a.forecast_date).localeCompare(String(b.forecast_date));
    })
  ), [forecast]);

  const topProduct = productSummary[0];
  const busiestDay = useMemo(() => {
    const totalsByDay = {};
    (forecast?.forecasts || []).forEach((row) => {
      totalsByDay[row.forecast_date] = (totalsByDay[row.forecast_date] || 0) + row.predicted_units;
    });
    const rankedDays = Object.entries(totalsByDay).sort((a, b) => b[1] - a[1]);
    return rankedDays[0] || null;
  }, [forecast]);

  const formatDateTime = (value) => (value
    ? new Date(value).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
    : '--');

  const formatTime = (value) => (value
    ? new Date(value).toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
    : '--');

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title">Sales forecast</h1>
            <p className="card-subtitle">See what may sell in the coming days, in a simple and easy way.</p>
          </div>
          <div className="toolbar">
            <select className="form-select compact-select" value={selectedStore} onChange={(e) => setSelectedStore(e.target.value)}>
              {stores.map((store) => <option key={store.store_id} value={store.store_id}>{store.name}</option>)}
            </select>
            <select className="form-select compact-select" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
            </select>
            <select className="form-select compact-select" value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="arima">Smart forecast</option>
              <option value="baseline">Simple forecast</option>
            </select>
            <button className="btn btn-primary" onClick={startForecast} disabled={running || !selectedStore}>
              <TrendingUp size={16} />
              {running ? 'Preparing...' : 'Run forecast'}
            </button>
          </div>
        </div>
        {pollingTaskId && <div className="alert alert-info">Forecast is being prepared. This usually takes a few seconds.</div>}
        {forecast && (
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-value">{Math.round(forecast.total_predicted)}</div><div className="stat-label">Expected sales</div></div>
            <div className="stat-card"><div className="stat-value success">{productSummary.length}</div><div className="stat-label">Products covered</div></div>
            <div className="stat-card">
              <div className="stat-value warning" style={{ fontSize: '2rem', lineHeight: 1.2, whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                {topProduct ? topProduct.sku_name : '--'}
              </div>
              <div className="stat-label">Top selling product</div>
            </div>
            <div className="stat-card"><div className="stat-value">{formatTime(forecast.last_run_at)}</div><div className="stat-label">Last updated (IST)</div></div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="skeleton-card" style={{ marginTop: '1.5rem', minHeight: '18rem' }} />
      ) : forecast?.forecasts?.length ? (
        <>
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div>
                <h2 className="card-title">Quick understanding</h2>
                <p className="card-subtitle">A short summary of what is likely to move fastest.</p>
              </div>
            </div>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{busiestDay ? Math.round(busiestDay[1]) : '--'}</div>
                <div className="stat-label">Most busy day sales</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{busiestDay ? busiestDay[0] : '--'}</div>
                <div className="stat-label">Most busy day</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{topProduct ? Math.round(topProduct.total_units) : '--'}</div>
                <div className="stat-label">Top product total sales</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{formatDateTime(forecast.generated_at)}</div>
                <div className="stat-label">Forecast made at (IST)</div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div>
                <h2 className="card-title">Products likely to sell more</h2>
                <p className="card-subtitle">Focus on these items first while planning stock.</p>
              </div>
            </div>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Total expected sales</th>
                    <th>Average per day</th>
                    <th>Festival effect</th>
                  </tr>
                </thead>
                <tbody>
                  {productSummary.slice(0, 10).map((item) => (
                    <tr key={item.sku_name}>
                      <td><strong>{item.sku_name}</strong></td>
                      <td>{item.total_units.toFixed(1)}</td>
                      <td>{item.avg_units.toFixed(1)}</td>
                      <td>{item.festival_boost_applied ? <span className="badge badge-medium">Higher due to festival</span> : 'Normal'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div>
                <h2 className="card-title">Day-by-day view</h2>
                <p className="card-subtitle">Use this to see what may sell on each upcoming day.</p>
              </div>
            </div>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Product</th>
                    <th>Expected sales</th>
                    <th>Expected range</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyForecastRows.slice(0, 20).map((row, index) => (
                    <tr key={`${row.sku_id}-${row.forecast_date}-${index}`}>
                      <td>{row.forecast_date}</td>
                      <td>{row.sku_name}</td>
                      <td>{row.predicted_units.toFixed(1)}</td>
                      <td>{row.confidence_lower?.toFixed(1)} - {row.confidence_upper?.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="alert alert-info" style={{ marginTop: '1rem' }}>
              <Clock3 size={16} style={{ marginRight: '0.5rem' }} />
              Tip: first focus on products with higher expected sales and lower current stock.
            </div>
          </div>
        </>
      ) : (
        <div className="card empty-state" style={{ marginTop: '1.5rem' }}>
          <RefreshCw size={48} />
          <h2>No forecast results yet</h2>
          <p>Run a forecast to see simple product demand estimates here.</p>
        </div>
      )}
    </div>
  );
}
