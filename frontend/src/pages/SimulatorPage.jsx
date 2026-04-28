import { useEffect, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { toast } from 'sonner';

import api from '../services/api';

export default function SimulatorPage() {
  const [stores, setStores] = useState([]);
  const [skus, setSkus] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [selectedSku, setSelectedSku] = useState('');
  const [priceChange, setPriceChange] = useState(0);
  const [demandChange, setDemandChange] = useState(0);
  const [festivalBoost, setFestivalBoost] = useState(1);

  useEffect(() => {
    api.getStores().then((rows) => {
      setStores(rows);
      if (rows.length) setSelectedStore(rows[0].store_id);
    }).catch((error) => toast.error(error.message));
  }, []);

  useEffect(() => {
    if (!selectedStore) return;
    api.getStoreSKUs(selectedStore).then((rows) => {
      setSkus(rows);
      if (rows.length) setSelectedSku(rows[0].sku_id);
    }).catch((error) => toast.error(error.message));
  }, [selectedStore]);

  const projection = useMemo(() => {
    const sku = skus.find((row) => row.sku_id === selectedSku);
    const baselineDemand = 25;
    const demandMultiplier = 1 + (demandChange / 100);
    const priceMultiplier = 1 + (priceChange / 100);
    const labels = Array.from({ length: 7 }, (_, index) => `Day ${index + 1}`);
    const demand = labels.map((_, index) => Math.max(0, baselineDemand * demandMultiplier * festivalBoost * (1 + index * 0.02)));
    const revenue = demand.map((units) => units * 100 * priceMultiplier);
    const stock = demand.map((_, index) => Math.max(0, (sku?.current_stock || 150) - demand.slice(0, index + 1).reduce((sum, value) => sum + value, 0)));
    return { labels, demand, revenue, stock };
  }, [selectedSku, skus, priceChange, demandChange, festivalBoost]);

  const askAI = () => {
    toast.message('Open InventAI Assistant and ask about this simulator scenario.');
  };

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title">What-if simulator</h1>
            <p className="card-subtitle">Adjust price, demand, and festival boost to see a lightweight projection.</p>
          </div>
          <button className="btn btn-primary" onClick={askAI}>Ask AI</button>
        </div>
        <div className="split-grid">
          <div>
            <label className="form-label">Store</label>
            <select className="form-select" value={selectedStore} onChange={(e) => setSelectedStore(e.target.value)}>
              {stores.map((store) => <option key={store.store_id} value={store.store_id}>{store.name}</option>)}
            </select>
            <label className="form-label" style={{ marginTop: '1rem' }}>Product</label>
            <select className="form-select" value={selectedSku} onChange={(e) => setSelectedSku(e.target.value)}>
              {skus.map((sku) => <option key={sku.sku_id} value={sku.sku_id}>{sku.sku_name}</option>)}
            </select>
          </div>
          <div>
            <label className="form-label">Price change %: {priceChange}</label>
            <input className="range-input" type="range" min="-30" max="30" value={priceChange} onChange={(e) => setPriceChange(Number(e.target.value))} />
            <label className="form-label">Demand change %: {demandChange}</label>
            <input className="range-input" type="range" min="-30" max="60" value={demandChange} onChange={(e) => setDemandChange(Number(e.target.value))} />
            <label className="form-label">Festival boost: {festivalBoost.toFixed(2)}x</label>
            <input className="range-input" type="range" min="1" max="2" step="0.05" value={festivalBoost} onChange={(e) => setFestivalBoost(Number(e.target.value))} />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="chart-container">
          <Line
            data={{
              labels: projection.labels,
              datasets: [
                { label: 'Projected revenue', data: projection.revenue, borderColor: '#f97316', tension: 0.3 },
                { label: 'Stock remaining', data: projection.stock, borderColor: '#22c55e', tension: 0.3 },
              ],
            }}
            options={{ responsive: true, maintainAspectRatio: false }}
          />
        </div>
      </div>
    </div>
  );
}
