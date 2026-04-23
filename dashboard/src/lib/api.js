const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  health:             ()                  => request('/health'),
  report:             ()                  => request('/report'),
  reports:            ()                  => request('/reports'),
  crawl:              ()                  => request('/crawl',              { method: 'POST' }),
  crawlStatus:        ()                  => request('/crawl/status'),
  crawlCancel:        ()                  => request('/crawl/cancel',       { method: 'POST' }),
  preprocess:         ()                  => request('/preprocess',         { method: 'POST' }),
  preprocessStatus:   ()                  => request('/preprocess/status'),
  preprocessCancel:   ()                  => request('/preprocess/cancel',  { method: 'POST' }),
  analyze:            ()                  => request('/analyze',            { method: 'POST' }),
  analyzeStatus:      ()                  => request('/analyze/status'),
  analyzeCancel:      ()                  => request('/analyze/cancel',     { method: 'POST' }),
  pipeline:           (skipCrawl = false) => request(`/pipeline${skipCrawl ? '?skip_crawl=true' : ''}`, { method: 'POST' }),
  pipelineStatus:     ()                  => request('/pipeline/status'),
  pipelineCancel:     ()                  => request('/pipeline/cancel',    { method: 'POST' }),
}