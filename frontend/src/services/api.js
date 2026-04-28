const rawApiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1';
const API_BASE = rawApiBase.endsWith('/api/v1')
  ? rawApiBase
  : `${rawApiBase.replace(/\/$/, '')}/api/v1`;

function getStoredToken() {
  return localStorage.getItem('inventai_token') || '';
}

function clearAuthAndRedirect() {
  localStorage.removeItem('inventai_token');
  localStorage.removeItem('inventai_user');
  if (window.location.pathname !== '/') {
    window.location.href = '/';
  }
}

function normalizeNetworkError(error) {
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch') {
      return new Error('Unable to reach the server. Check your connection and try again.');
    }
    return error;
  }
  return new Error('An unexpected network error occurred.');
}

async function handleResponse(response) {
  if (response.status === 401) {
    clearAuthAndRedirect();
    throw new Error('Your session expired. Please sign in again.');
  }

  if (!response.ok) {
    let detail = 'Request failed';
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || JSON.stringify(payload);
    } catch {
      detail = `Server returned ${response.status}: ${response.statusText}`;
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function handleStreamingResponse(response) {
  if (response.status === 401) {
    clearAuthAndRedirect();
    throw new Error('Your session expired. Please sign in again.');
  }

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    let detail = 'Request failed';
    try {
      if (contentType.includes('application/json')) {
        const payload = await response.json();
        detail = payload.detail || payload.message || JSON.stringify(payload);
      } else {
        detail = (await response.text()) || `Server returned ${response.status}: ${response.statusText}`;
      }
    } catch {
      detail = `Server returned ${response.status}: ${response.statusText}`;
    }
    throw new Error(detail);
  }

  return response;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getStoredToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    return handleResponse(response);
  } catch (error) {
    throw normalizeNetworkError(error);
  }
}

export const api = {
  async googleAuth(credential) {
    return request('/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    });
  },
  async me() {
    return request('/auth/me');
  },
  async health() {
    return request('/health');
  },
  async getStores() {
    return request('/products/stores');
  },
  async getStore(storeId) {
    return request(`/products/stores/${storeId}`);
  },
  async getStoreSKUs(storeId) {
    return request(`/products/stores/${storeId}/skus`);
  },
  async updateStock(storeId, updates) {
    return request(`/products/stores/${storeId}/update-stock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
  },
  async uploadPreview(file, mapping = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (mapping) formData.append('mapping', JSON.stringify(mapping));
    return request('/products/upload-preview', { method: 'POST', body: formData });
  },
  async uploadSales(file, mapping = null, excludedRows = []) {
    const formData = new FormData();
    formData.append('file', file);
    if (mapping) formData.append('mapping', JSON.stringify(mapping));
    formData.append('excluded_rows', JSON.stringify(excludedRows));
    return request('/products/upload-sales', { method: 'POST', body: formData });
  },
  async runForecast(storeId, horizon = 7, skuIds = null, model = 'arima') {
    return request('/forecast/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store_id: storeId, horizon, sku_ids: skuIds, model }),
    });
  },
  async getForecastStatus(taskId) {
    return request(`/forecast/status/${taskId}`);
  },
  async getForecast(storeId, horizon = 7, skuId = null) {
    const params = new URLSearchParams({ store_id: storeId, horizon: String(horizon) });
    if (skuId) params.set('sku_id', skuId);
    return request(`/forecast?${params.toString()}`);
  },
  async getReorderList(storeId, horizon = 7, regenerate = true) {
    const params = new URLSearchParams({ store_id: storeId, horizon: String(horizon), regenerate: String(regenerate) });
    return request(`/reorder/list?${params.toString()}`);
  },
  async getReorderSummary(storeId) {
    return request(`/reorder/summary?store_id=${encodeURIComponent(storeId)}`);
  },
  async getMandiPrices(commodity = null, state = null) {
    const params = new URLSearchParams();
    if (commodity) params.set('commodity', commodity);
    if (state) params.set('state', state);
    return request(`/mandi/prices${params.toString() ? `?${params.toString()}` : ''}`);
  },
  async getAlerts() {
    return request('/alerts');
  },
  async dismissAlert(alertId) {
    return request(`/alerts/${alertId}/dismiss`, { method: 'POST' });
  },
  async getSettings() {
    return request('/settings');
  },
  async updateSettings(payload) {
    return request('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },
  async getFestivals() {
    return request('/settings/festivals');
  },
  async seedFestivals(year) {
    return request(`/settings/festivals/seed?year=${year}`, { method: 'POST' });
  },
  streamChat(payload) {
    const token = getStoredToken();
    return fetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })
      .then(handleStreamingResponse)
      .catch((error) => {
        throw normalizeNetworkError(error);
      });
  },
};

export function clearAuthStorage() {
  localStorage.removeItem('inventai_token');
  localStorage.removeItem('inventai_user');
}

export default api;
