import { useEffect, useMemo, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import api from '../services/api';
import SortableHeader from '../components/ui/sortable-header';

function normalizeUrgency(urgency) {
  return String(urgency || '').trim().toLowerCase();
}

function compareValues(left, right, direction) {
  const normalizedLeft = left ?? '';
  const normalizedRight = right ?? '';

  if (typeof normalizedLeft === 'number' && typeof normalizedRight === 'number') {
    return direction === 'asc' ? normalizedLeft - normalizedRight : normalizedRight - normalizedLeft;
  }

  return direction === 'asc'
    ? String(normalizedLeft).localeCompare(String(normalizedRight))
    : String(normalizedRight).localeCompare(String(normalizedLeft));
}

export default function ReorderPage() {
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [horizon, setHorizon] = useState(7);
  const [reorderList, setReorderList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tableSort, setTableSort] = useState({ key: 'urgency', direction: 'asc' });

  useEffect(() => {
    api.getStores().then((rows) => {
      setStores(rows);
      if (rows.length) setSelectedStore(rows[0].store_id);
    }).catch((error) => toast.error(error.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedStore) return;

    let isActive = true;
    const run = async () => {
      setLoading(true);
      try {
        const response = await api.getReorderList(selectedStore, horizon, true);
        if (isActive) {
          setReorderList(response);
        }
      } catch (error) {
        if (isActive) {
          toast.error(error.message);
        }
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      isActive = false;
    };
  }, [selectedStore, horizon]);

  const loadReorderList = async () => {
    setLoading(true);
    try {
      const response = await api.getReorderList(selectedStore, horizon, true);
      setReorderList(response);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const sortedItems = useMemo(() => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return [...(reorderList?.items || [])].sort((a, b) => {
      if (tableSort.key === 'urgency') {
        const left = normalizeUrgency(a.urgency);
        const right = normalizeUrgency(b.urgency);
        return tableSort.direction === 'asc'
          ? (order[left] ?? Number.MAX_SAFE_INTEGER) - (order[right] ?? Number.MAX_SAFE_INTEGER)
          : (order[right] ?? Number.MAX_SAFE_INTEGER) - (order[left] ?? Number.MAX_SAFE_INTEGER);
      }
      return compareValues(a[tableSort.key], b[tableSort.key], tableSort.direction);
    });
  }, [reorderList, tableSort]);

  const handleSort = (column) => {
    setTableSort((current) => ({
      key: column,
      direction: current.key === column && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const exportCsv = () => {
    if (!sortedItems.length) return;
    const rows = ['Product,Qty,Urgency,Reason'];
    sortedItems.forEach((item) => rows.push(`"${item.sku_name}",${item.reorder_qty},${item.urgency},"${item.reason}"`));
    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'inventai-purchase-order.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title">Reorder priorities</h1>
            <p className="card-subtitle">Critical under 3 days, warning under 7 days, and healthier items below that.</p>
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
            <button className="btn btn-primary" onClick={loadReorderList}><RefreshCw size={16} />Refresh</button>
            <button className="btn btn-ghost" onClick={exportCsv}><Download size={16} />Generate Purchase Order</button>
          </div>
        </div>
      </div>

      {loading ? <div className="skeleton-card" style={{ marginTop: '1.5rem', minHeight: '18rem' }} /> : null}

      {!loading && reorderList?.items?.length ? (
        <>
          <div className="stats-grid" style={{ marginTop: '1.5rem' }}>
            <div className="stat-card"><div className="stat-value">{reorderList.total_items}</div><div className="stat-label">Items</div></div>
            <div className="stat-card"><div className="stat-value critical">{sortedItems.filter((item) => item.urgency === 'critical').length}</div><div className="stat-label">Critical</div></div>
            <div className="stat-card"><div className="stat-value high">{sortedItems.filter((item) => item.urgency === 'high').length}</div><div className="stat-label">Warning</div></div>
            <div className="stat-card"><div className="stat-value success">{sortedItems.filter((item) => item.urgency === 'low').length}</div><div className="stat-label">OK</div></div>
          </div>
          <div className="card">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <SortableHeader label="Product" column="sku_name" sortConfig={tableSort} onSort={handleSort} />
                    <SortableHeader label="Priority" column="urgency" sortConfig={tableSort} onSort={handleSort} />
                    <SortableHeader label="Order Qty" column="reorder_qty" sortConfig={tableSort} onSort={handleSort} />
                    <SortableHeader label="Current Stock" column="current_stock" sortConfig={tableSort} onSort={handleSort} />
                    <SortableHeader label="Forecasted Demand" column="forecasted_demand" sortConfig={tableSort} onSort={handleSort} />
                    <SortableHeader label="Reason" column="reason" sortConfig={tableSort} onSort={handleSort} />
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((item) => (
                    <tr key={item.sku_id} className={normalizeUrgency(item.urgency) === 'critical' ? 'table-row-critical' : normalizeUrgency(item.urgency) === 'high' ? 'table-row-high' : ''}>
                      <td><strong>{item.sku_name}</strong><div className="card-subtitle">{item.sku_id}</div></td>
                      <td><span className={`badge badge-${normalizeUrgency(item.urgency) === 'critical' ? 'critical' : normalizeUrgency(item.urgency) === 'high' ? 'high' : normalizeUrgency(item.urgency) === 'medium' ? 'medium' : 'low'}`}>{normalizeUrgency(item.urgency) || 'unknown'}</span></td>
                      <td>{item.reorder_qty}</td>
                      <td>{item.current_stock}</td>
                      <td>{item.forecasted_demand}</td>
                      <td>{item.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}

      {!loading && !reorderList?.items?.length ? (
        <div className="card empty-state" style={{ marginTop: '1.5rem' }}>
          <h2>No reorder recommendations right now</h2>
          <p>Upload more sales history or run a new forecast to generate purchase suggestions.</p>
        </div>
      ) : null}
    </div>
  );
}
