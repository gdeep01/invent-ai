import { useMemo, useState } from 'react';
import { Check, CheckCircle2, CircleAlert, MessageCircle, Sparkles, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import ChatBot from '../components/ChatBot';
import SortableHeader from '../components/ui/sortable-header';
import api from '../services/api';

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

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [excludedRows, setExcludedRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showChatBot, setShowChatBot] = useState(false);
  const [mappingSort, setMappingSort] = useState({ key: 'source', direction: 'asc' });
  const [anomalySort, setAnomalySort] = useState({ key: 'date', direction: 'desc' });
  const [isDragActive, setIsDragActive] = useState(false);

  const previewFile = async () => {
    if (!file) return;
    setLoading(true);
    setUploadResult(null);
    try {
      const response = await api.uploadPreview(file);
      setPreview(response);
      toast.success(response.success ? 'CSV preview ready' : 'Preview detected mapping issues');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const processUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const response = await api.uploadSales(file, preview?.suggestion?.mapping, excludedRows);
      setUploadResult(response);
      toast[response.success ? 'success' : 'error'](
        response.success ? 'CSV processed successfully' : (response.errors?.[0] || 'CSV processing failed'),
      );
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleExcludedRow = (rowIndex) => {
    setExcludedRows((current) => current.includes(rowIndex) ? current.filter((value) => value !== rowIndex) : [...current, rowIndex]);
  };

  const onFileChange = (nextFile) => {
    setFile(nextFile);
    setPreview(null);
    setUploadResult(null);
    setExcludedRows([]);
  };

  const formatFileSize = (size) => {
    if (!size) return '0 KB';
    if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleSortChange = (setter) => (column) => {
    setter((current) => ({
      key: column,
      direction: current.key === column && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const mappingStatusRows = useMemo(() => {
    const mappingEntries = Object.entries(preview?.suggestion?.mapping || {});
    const reverseMap = Object.fromEntries(mappingEntries.map(([source, target]) => [target, source]));
    const defaultedFields = ['store_id', 'sku_name'];
    const requiredFields = ['sku_id', 'date', 'units_sold'];
    const optionalFields = ['price', 'discount', 'category'];

    return [...defaultedFields, ...requiredFields, ...optionalFields].map((field) => ({
      field,
      source: reverseMap[field] || '--',
      status: reverseMap[field]
        ? 'mapped'
        : defaultedFields.includes(field)
          ? 'defaulted'
          : requiredFields.includes(field)
            ? 'missing'
            : 'optional',
    }));
  }, [preview]);

  const sortedMappingStatusRows = useMemo(() => {
    const rows = [...mappingStatusRows];
    return rows.sort((a, b) => compareValues(a[mappingSort.key], b[mappingSort.key], mappingSort.direction));
  }, [mappingStatusRows, mappingSort]);

  const sortedAnomalies = useMemo(() => {
    const rows = [...(preview?.anomalies || [])];
    return rows.sort((a, b) => {
      if (anomalySort.key === 'exclude') {
        return compareValues(excludedRows.includes(a.row_index), excludedRows.includes(b.row_index), anomalySort.direction);
      }
      return compareValues(a[anomalySort.key], b[anomalySort.key], anomalySort.direction);
    });
  }, [preview, anomalySort, excludedRows]);

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title">Upload sales file</h1>
            <p className="card-subtitle">Check the file, review unusual rows, then upload it.</p>
          </div>
        </div>
        <label
          className={`upload-area ${isDragActive ? 'upload-area-active' : ''}`}
          onDragEnter={() => setIsDragActive(true)}
          onDragLeave={() => setIsDragActive(false)}
          onDrop={() => setIsDragActive(false)}
        >
          <input className="upload-input" type="file" accept=".csv" onChange={(e) => e.target.files?.[0] && onFileChange(e.target.files[0])} />
          <div className="upload-copy">
            <h2>Drop your sales file here or click to choose it</h2>
            <p>Use a `.csv` file up to 5MB.</p>
          </div>
          <span className="btn btn-ghost upload-browse-button">Choose file</span>
          {file ? (
            <div className="upload-file-pill">
              <span className="upload-file-name">{file.name}</span>
              <span className="upload-file-size">{formatFileSize(file.size)}</span>
            </div>
          ) : null}
        </label>
        <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" onClick={previewFile} disabled={!file || loading}>
            Check file
          </button>
        </div>
      </div>

      {preview ? (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <div>
              <h2 className="card-title">File check</h2>
              <p className="card-subtitle">
                {preview?.suggestion?.used_ai
                  ? 'AI helped match your file columns.'
                  : 'Column names were matched automatically where possible.'}
              </p>
            </div>
            <button className="btn btn-primary" onClick={processUpload} disabled={loading || !preview.success}>
              <Sparkles size={16} />
              Upload file
            </button>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <SortableHeader label="Field" column="field" sortConfig={mappingSort} onSort={handleSortChange(setMappingSort)} />
                  <SortableHeader label="File Column" column="source" sortConfig={mappingSort} onSort={handleSortChange(setMappingSort)} />
                  <SortableHeader label="Status" column="status" sortConfig={mappingSort} onSort={handleSortChange(setMappingSort)} />
                </tr>
              </thead>
              <tbody>
                {sortedMappingStatusRows.map(({ field, source, status }) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td>{source}</td>
                    <td>
                      <span className={`table-status ${status}`}>
                        {status === 'mapped' || status === 'defaulted' ? <Check size={14} /> : <X size={14} />}
                        <span>
                          {status === 'mapped'
                            ? 'Mapped'
                            : status === 'defaulted'
                              ? 'Defaulted'
                              : status === 'missing'
                                ? 'Missing'
                                : 'Optional'}
                        </span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {preview?.anomalies?.length ? (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <div>
              <h2 className="card-title">Check unusual rows</h2>
              <p className="card-subtitle">If a row looks wrong, tick it so it does not affect the forecast.</p>
            </div>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <SortableHeader label="Exclude" column="exclude" sortConfig={anomalySort} onSort={handleSortChange(setAnomalySort)} />
                  <SortableHeader label="Product" column="sku_name" sortConfig={anomalySort} onSort={handleSortChange(setAnomalySort)} />
                  <SortableHeader label="Date" column="date" sortConfig={anomalySort} onSort={handleSortChange(setAnomalySort)} />
                  <SortableHeader label="Units Sold" column="units_sold" sortConfig={anomalySort} onSort={handleSortChange(setAnomalySort)} />
                  <SortableHeader label="Note" column="note" sortConfig={anomalySort} onSort={handleSortChange(setAnomalySort)} />
                </tr>
              </thead>
              <tbody>
                {sortedAnomalies.map((anomaly) => (
                  <tr key={`${anomaly.row_index}-${anomaly.sku_name}`}>
                    <td><input type="checkbox" checked={excludedRows.includes(anomaly.row_index)} onChange={() => toggleExcludedRow(anomaly.row_index)} /></td>
                    <td>{anomaly.sku_name}</td>
                    <td>{anomaly.date}</td>
                    <td>{anomaly.units_sold}</td>
                    <td>{anomaly.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {uploadResult?.success ? (
        <div className="alert alert-success" style={{ marginTop: '1.5rem' }}>
          <CheckCircle2 size={18} style={{ marginRight: '0.5rem' }} />
          Uploaded {uploadResult.rows_processed} rows for store {uploadResult.store_id}. You can now run the forecast.
        </div>
      ) : null}

      {uploadResult?.success && (
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link
            to="/forecast"
            className="btn btn-ghost"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Sparkles size={16} />
            Open Forecast
          </Link>
          <button
            className="btn btn-primary"
            onClick={() => setShowChatBot(!showChatBot)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <MessageCircle size={16} />
            {showChatBot ? 'Close Help' : 'Ask for Help'}
          </button>
        </div>
      )}

      {uploadResult?.success && showChatBot && (
        <div style={{ marginTop: '1.5rem' }}>
          <ChatBot onClose={() => setShowChatBot(false)} />
        </div>
      )}

      {!loading && preview && !preview.success ? (
        <div className="alert alert-error upload-warning-banner" style={{ marginTop: '1.5rem' }}>
          <CircleAlert size={18} />
          <span>This file still needs a few required columns before it can be uploaded.</span>
        </div>
      ) : null}
    </div>
  );
}
