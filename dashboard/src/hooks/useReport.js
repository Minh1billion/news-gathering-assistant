import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../lib/api'

export function useReport() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [excludedKeywords, setExcludedKeywords] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem('excluded_keywords') || '[]'))
    } catch {
      return new Set()
    }
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.report()
      setReport(data)
    } catch (e) {
      if (e.message.startsWith('404')) setReport(null)
      else setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const excludeKeyword = useCallback((keyword) => {
    setExcludedKeywords(prev => {
      const next = new Set(prev)
      next.add(keyword)
      localStorage.setItem('excluded_keywords', JSON.stringify([...next]))
      return next
    })
  }, [])

  const resetExcluded = useCallback(() => {
    setExcludedKeywords(new Set())
    localStorage.removeItem('excluded_keywords')
  }, [])

  const filteredReport = useMemo(() => {
    if (!report) return report
    return report
  }, [report])

  return {
    report: filteredReport,
    loading,
    error,
    reload: load,
    excludedKeywords,
    excludeKeyword,
    resetExcluded,
  }
}

export function useHealth() {
  const [ready, setReady] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      while (!cancelled) {
        try {
          const h = await api.health()
          if (h.ready) { setReady(true); setChecking(false); return }
        } catch {}
        await new Promise(r => setTimeout(r, 2000))
      }
    }
    poll()
    return () => { cancelled = true }
  }, [])

  return { ready, checking }
}