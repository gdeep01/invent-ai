import { useEffect, useMemo, useState } from 'react';
import { KeyRound, PartyPopper, Save } from 'lucide-react';
import { toast } from 'sonner';

import api from '../services/api';
import SortableHeader from '../components/ui/sortable-header';

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

export default function SettingsPage() {
  const [settings, setSettings] = useState({ gemini_api_key: '', notification_threshold_days: 7, festival_multipliers: [] });
  const [festivals, setFestivals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [multiplierSort, setMultiplierSort] = useState({ key: 'category', direction: 'asc' });
  const [festivalSort, setFestivalSort] = useState({ key: 'date', direction: 'asc' });

  useEffect(() => {
    Promise.all([api.getSettings(), api.getFestivals()]).then(([settingsResponse, festivalRows]) => {
      setSettings({
        gemini_api_key: '',
        notification_threshold_days: settingsResponse.notification_threshold_days,
        festival_multipliers: settingsResponse.festival_multipliers.length ? settingsResponse.festival_multipliers : [
          { category: 'sweets', multiplier: 1.4 },
          { category: 'oil', multiplier: 1.25 },
        ],
      });
      setFestivals(festivalRows);
    }).catch((error) => toast.error(error.message)).finally(() => setLoading(false));
  }, []);

  const updateMultiplier = (index, key, value) => {
    setSettings((current) => {
      const next = [...current.festival_multipliers];
      next[index] = { ...next[index], [key]: key === 'multiplier' ? Number(value) : value };
      return { ...current, festival_multipliers: next };
    });
  };

  const saveSettings = async () => {
    await api.updateSettings(settings);
    toast.success('Settings saved');
  };

  const seedFestivals = async () => {
    await api.seedFestivals(new Date().getFullYear());
    const rows = await api.getFestivals();
    setFestivals(rows);
    toast.success('Festival calendar seeded');
  };

  const sortedMultipliers = useMemo(() => {
    return settings.festival_multipliers
      .map((row, index) => ({ row, originalIndex: index }))
      .sort((a, b) => compareValues(a.row[multiplierSort.key], b.row[multiplierSort.key], multiplierSort.direction));
  }, [settings.festival_multipliers, multiplierSort]);

  const sortedFestivals = useMemo(() => {
    return [...festivals].sort((a, b) => compareValues(a[festivalSort.key], b[festivalSort.key], festivalSort.direction));
  }, [festivals, festivalSort]);

  const handleSortChange = (setter) => (column) => {
    setter((current) => ({
      key: column,
      direction: current.key === column && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  if (loading) {
    return <div className="skeleton-card" style={{ minHeight: '20rem' }} />;
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title">Settings</h1>
            <p className="card-subtitle">Configure Gemini access, festival multipliers, and notification thresholds.</p>
          </div>
          <button className="btn btn-primary" onClick={saveSettings}><Save size={16} />Save</button>
        </div>
        <div className="form-group">
          <label className="form-label"><KeyRound size={16} style={{ marginRight: '0.5rem' }} />Gemini API key</label>
          <input className="form-input" type="password" placeholder="Paste your Gemini API key" value={settings.gemini_api_key} onChange={(e) => setSettings((current) => ({ ...current, gemini_api_key: e.target.value }))} />
        </div>
        <div className="form-group">
          <label className="form-label">Notification threshold in days</label>
          <input className="form-input" type="number" min="1" max="60" value={settings.notification_threshold_days} onChange={(e) => setSettings((current) => ({ ...current, notification_threshold_days: Number(e.target.value) }))} />
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">Festival multipliers</h2>
            <p className="card-subtitle">These multipliers influence the forecast-side festival boost logic.</p>
          </div>
        </div>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <SortableHeader label="Category" column="category" sortConfig={multiplierSort} onSort={handleSortChange(setMultiplierSort)} />
                <SortableHeader label="Multiplier" column="multiplier" sortConfig={multiplierSort} onSort={handleSortChange(setMultiplierSort)} />
              </tr>
            </thead>
            <tbody>
              {sortedMultipliers.map(({ row, originalIndex }) => (
                <tr key={`${row.category}-${originalIndex}`}>
                  <td><input className="form-input" value={row.category} onChange={(e) => updateMultiplier(originalIndex, 'category', e.target.value)} /></td>
                  <td><input className="form-input" type="number" step="0.05" min="0.1" max="5" value={row.multiplier} onChange={(e) => updateMultiplier(originalIndex, 'multiplier', e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <div>
            <h2 className="card-title"><PartyPopper size={18} style={{ marginRight: '0.5rem' }} />Festival calendar</h2>
            <p className="card-subtitle">Upcoming festivals used by the demand boost service.</p>
          </div>
          <button className="btn btn-ghost" onClick={seedFestivals}>Seed festivals</button>
        </div>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <SortableHeader label="Name" column="name" sortConfig={festivalSort} onSort={handleSortChange(setFestivalSort)} />
                <SortableHeader label="Date" column="date" sortConfig={festivalSort} onSort={handleSortChange(setFestivalSort)} />
                <SortableHeader label="Region" column="region" sortConfig={festivalSort} onSort={handleSortChange(setFestivalSort)} />
                <SortableHeader label="Impact" column="impact_multiplier" sortConfig={festivalSort} onSort={handleSortChange(setFestivalSort)} />
              </tr>
            </thead>
            <tbody>
              {sortedFestivals.map((festival) => (
                <tr key={`${festival.name}-${festival.date}`}>
                  <td>{festival.name}</td>
                  <td>{festival.date}</td>
                  <td>{festival.region || 'All India'}</td>
                  <td>{festival.impact_multiplier}x</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
