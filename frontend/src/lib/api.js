/**
 * Thin API client for the BullBear FastAPI backend.
 * Stores the JWT in localStorage and attaches it as a Bearer token.
 */
const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
const TOKEN_KEY = 'bb_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request(path, { method = 'GET', body, form, file, auth = true, headers = {} } = {}) {
  const h = { ...headers }
  const opts = { method }

  if (auth) {
    const t = getToken()
    if (t) h['Authorization'] = `Bearer ${t}`
  }
  if (file) {
    // multipart/form-data: leave Content-Type unset so the browser sets the boundary.
    const fd = new FormData()
    fd.append('file', file)
    opts.body = fd
  } else if (form) {
    h['Content-Type'] = 'application/x-www-form-urlencoded'
    opts.body = new URLSearchParams(form).toString()
  } else if (body !== undefined) {
    h['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  opts.headers = h

  let res
  try {
    res = await fetch(`${BASE}${path}`, opts)
  } catch {
    throw new Error('Cannot reach the API. Is the backend running on port 8000?')
  }

  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    const msg = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d) => d.msg).join('; ')
        : `Request failed (${res.status})`
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  // auth
  login: (email, password) =>
    request('/auth/login', { method: 'POST', form: { username: email, password }, auth: false }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  me: () => request('/auth/me'),

  // market (public)
  overview: () => request('/market/overview', { auth: false }),
  tickers: () => request('/market/tickers', { auth: false }),
  quotes: () => request('/market/quotes', { auth: false }),
  series: (symbol, range) => request(`/market/series/${symbol}?range=${range}`, { auth: false }),
  predict: (symbol, horizon = 1) =>
    request('/market/predict', { method: 'POST', body: { symbol, horizon_days: horizon }, auth: false }),
  predictionSeries: (symbol, horizon = 1) =>
    request(`/market/prediction-series/${symbol}?horizon=${horizon}`, { auth: false }),

  // user-scoped
  portfolio: () => request('/portfolio'),
  importPortfolio: (file) => request('/portfolio/import', { method: 'POST', file }),
  placeOrder: (payload) => request('/orders', { method: 'POST', body: payload }),
  orders: () => request('/orders'),
  transactions: (side) => request(`/transactions${side ? `?side=${side}` : ''}`),

  // admin
  adminUsers: () => request('/admin/users'),
  adminDatasets: () => request('/admin/datasets'),
  createDataset: (payload) => request('/admin/datasets', { method: 'POST', body: payload }),
  deleteDataset: (id) => request(`/admin/datasets/${id}`, { method: 'DELETE' }),
}
