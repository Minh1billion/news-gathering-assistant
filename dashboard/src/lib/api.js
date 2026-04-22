const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  health: () => request('/health'),
  report: () => request('/report'),
  reports: () => request('/reports'),
  crawl: () => request('/crawl', { method: 'POST' }),
  preprocess: () => request('/preprocess', { method: 'POST' }),
  analyze: () => request('/analyze', { method: 'POST' }),
  pipeline: (skipCrawl = false) =>
    request(`/pipeline${skipCrawl ? '?skip_crawl=true' : ''}`, { method: 'POST' }),
}