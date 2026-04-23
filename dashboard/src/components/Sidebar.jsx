import { useState, useEffect } from 'react'
import { topicColor } from '../lib/utils'
import { Btn, Spinner } from './ui'
import { api } from '../lib/api'

function NavLabel({ children }) {
  return <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--sidebar-muted)', margin: '20px 0 8px' }}>{children}</p>
}

function Divider() {
  return <div style={{ height: 1, background: '#2a2a2a', margin: '16px 0' }} />
}

const CANCEL_API = {
  pipeline:   api.pipelineCancel,
  crawl:      api.crawlCancel,
  preprocess: api.preprocessCancel,
  analyze:    api.analyzeCancel,
}

const STATUS_API = {
  pipeline:   api.pipelineStatus,
  crawl:      api.crawlStatus,
  preprocess: api.preprocessStatus,
  analyze:    api.analyzeStatus,
}

const LABEL = {
  pipeline:   'Pipeline',
  crawl:      'Crawl',
  preprocess: 'Preprocess',
  analyze:    'Analyze',
}

export function Sidebar({ report, reports, onReload }) {
  const [running, setRunning] = useState(null)
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    Promise.allSettled(
      Object.entries(STATUS_API).map(([key, fn]) => fn().then(s => ({ key, running: s.running })))
    ).then(results => {
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value.running) {
          setRunning(r.value.key)
          break
        }
      }
    })
  }, [])

  async function run(action, label) {
    setRunning(label)
    setCancelling(false)
    try {
      await action()
      onReload()
    } catch (e) {
      if (!e.message.startsWith('499')) alert(e.message)
    } finally {
      setRunning(null)
      setCancelling(false)
    }
  }

  async function handleCancel() {
    if (!running || !CANCEL_API[running]) return
    setCancelling(true)
    try {
      await CANCEL_API[running]()
    } catch (e) {
      alert(e.message)
      setCancelling(false)
    }
  }

  const canCancel = running && !!CANCEL_API[running]

  return (
    <aside className="sidebar" style={{ position: 'fixed', top: 0, left: 0, height: '100vh', width: 240, background: 'var(--sidebar-bg)', padding: '24px 20px', overflowY: 'auto', zIndex: 100, display: 'flex', flexDirection: 'column', gap: 0 }}>
      <div style={{ marginBottom: 4 }}>
        <p style={{ fontFamily: 'var(--mono)', fontSize: '0.95rem', fontWeight: 600, color: '#f0ede8', letterSpacing: '-0.01em' }}>◈ NEWS INTELLIGENCE</p>
        <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--sidebar-muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: 2 }}>Operations Dashboard</p>
      </div>

      <Divider />

      <NavLabel>Pipeline Control</NavLabel>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {canCancel ? (
          <Btn
            variant="ghost"
            onClick={handleCancel}
            disabled={cancelling}
            style={{
              width: '100%',
              background: 'rgba(220,60,60,0.15)',
              color: cancelling ? 'var(--sidebar-muted)' : '#e07070',
              border: '1px solid rgba(220,60,60,0.3)',
            }}
          >
            {cancelling ? '⟳ Cancelling...' : `✕ Cancel ${LABEL[running]}`}
          </Btn>
        ) : (
          <Btn
            variant="ghost"
            onClick={() => run(api.pipeline, 'pipeline')}
            disabled={!!running}
            style={{ width: '100%' }}
          >
            Run Full Pipeline
          </Btn>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {[
            ['Crawl',      'crawl',      api.crawl],
            ['Preprocess', 'preprocess', api.preprocess],
            ['Analyze',    'analyze',    api.analyze],
            ['Refresh',    'refresh',    async () => {}],
          ].map(([label, key, action]) => (
            <Btn
              key={key}
              variant="ghost"
              disabled={!!running}
              onClick={() => run(action, key)}
              style={{ fontSize: '0.65rem', padding: '6px 8px' }}
            >
              {running === key ? '⟳' : label}
            </Btn>
          ))}
        </div>
      </div>

      {running && !cancelling && <Spinner text={`${LABEL[running] ?? running} running…`} />}
      {cancelling && <Spinner text="stopping…" />}

      <Divider />

      {report && (
        <>
          <NavLabel>Report Period</NavLabel>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.75rem', color: 'var(--sidebar-text)', marginBottom: 2 }}>{report.week_start} — {report.week_end}</p>

          <Divider />

          <NavLabel>Topic Breakdown</NavLabel>
          {report.topic_distribution.map(td => {
            const color = topicColor(td.topic)
            return (
              <div key={td.topic} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: '0.68rem', marginBottom: 3 }}>
                  <span style={{ color }}>{td.topic}</span>
                  <span style={{ color: 'var(--sidebar-muted)' }}>{td.count}</span>
                </div>
                <div style={{ height: 2, background: '#2a2a2a' }}>
                  <div style={{ height: 2, background: color, width: `${td.percentage}%` }} />
                </div>
              </div>
            )
          })}

          <Divider />
        </>
      )}

      <NavLabel>Saved Reports</NavLabel>
      {reports.length === 0
        ? <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: '#6b6860' }}>No saved reports yet</p>
        : reports.slice(0, 5).map(r => (
          <p key={r.filename} style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--sidebar-muted)', marginBottom: 4 }}>
            ↳ {r.week_start}–{r.week_end} <span style={{ color: '#6b6860' }}>({r.total_articles} art.)</span>
          </p>
        ))
      }
    </aside>
  )
}