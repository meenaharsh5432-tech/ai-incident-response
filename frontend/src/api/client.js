import axios from 'axios'

function resolveBaseUrl() {
  const configured = import.meta.env.VITE_API_URL?.trim()
  if (!configured) return ''
  return configured.endsWith('/') ? configured.slice(0, -1) : configured
}

function extractMessage(error) {
  if (!error) return 'Request failed.'
  if (!axios.isAxiosError(error)) return error.message || 'Request failed.'

  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || String(item))
      .filter(Boolean)
      .join(', ')
  }

  return error.message || 'Request failed.'
}

const api = axios.create({
  baseURL: resolveBaseUrl(),
  timeout: 15000,
  headers: {
    Accept: 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const wrapped = new Error(extractMessage(error))
    wrapped.status = error.response?.status
    wrapped.cause = error
    return Promise.reject(wrapped)
  },
)

function unwrap(request) {
  return request.then((response) => response.data)
}

export function getErrorMessage(error, fallback = 'Something went wrong.') {
  return error?.message || fallback
}

export const getHealth = () => unwrap(api.get('/api/health'))
export const getStats = () => unwrap(api.get('/api/stats'))
export const getIncidents = (params = {}) => unwrap(api.get('/api/incidents', { params }))
export const getIncident = (id) => unwrap(api.get(`/api/incidents/${id}`))
// Longer timeout: Groq call can take up to ~65s (30s timeout + 5s sleep + 30s retry)
export const diagnoseIncident = (id) => unwrap(api.get(`/api/incidents/${id}/diagnose`, { timeout: 70000 }))
export const resolveIncident = (id, notes) =>
  unwrap(api.post(`/api/incidents/${id}/resolve`, { resolution_notes: notes }))
export const submitFeedback = (id, wasHelpful, actualFix) =>
  unwrap(api.post(`/api/incidents/${id}/feedback`, { was_helpful: wasHelpful, actual_fix: actualFix }))
export const ingestError = (payload) => unwrap(api.post('/api/errors', payload))
export const listApiKeys = () => unwrap(api.get('/api/keys'))
export const createApiKey = (serviceName) =>
  unwrap(api.post('/api/keys', { service_name: serviceName }))
export const revokeApiKey = (id) => api.delete(`/api/keys/${id}`)
