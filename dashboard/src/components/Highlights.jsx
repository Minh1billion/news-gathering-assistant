import { useState, useMemo } from 'react'
import { SectionRule, TopicTag } from './ui'
import { fmtDate, topicColor } from '../lib/utils'

export function Highlights({ articles }) {
  const [selTopics, setSelTopics] = useState([])
  const [selSources, setSelSources] = useState([])
  const [minScore, setMinScore] = useState(0)

  const allTopics = useMemo(() => [...new Set(articles.map(a => a.topic))].sort(), [articles])
  const allSources = useMemo(() => [...new Set(articles.map(a => a.source))].sort(), [articles])

  const filtered = useMemo(() => articles.filter(a =>
    (!selTopics.length || selTopics.includes(a.topic)) &&
    (!selSources.length || selSources.includes(a.source)) &&
    a.tech_score >= minScore
  ), [articles, selTopics, selSources, minScore])

  function toggleTopic(t) {
    setSelTopics(p => p.includes(t) ? p.filter(x => x !== t) : [...p, t])
  }
  function toggleSource(s) {
    setSelSources(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])
  }

  return (
    <div>
      <SectionRule label="Highlighted Articles" />

      <div className="no-print" style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>Topic</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {allTopics.map(t => {
              const active = selTopics.includes(t)
              const color = topicColor(t)
              return (
                <button key={t} onClick={() => toggleTopic(t)} style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '3px 8px', border: `1px solid ${active ? color : 'var(--border-2)'}`, background: active ? color : 'transparent', color: active ? '#fff' : 'var(--ink-3)', borderRadius: 2, cursor: 'pointer', transition: 'all 0.15s' }}>
                  {t}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>Source</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {allSources.map(s => {
              const active = selSources.includes(s)
              return (
                <button key={s} onClick={() => toggleSource(s)} style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '3px 8px', border: `1px solid ${active ? 'var(--ink)' : 'var(--border-2)'}`, background: active ? 'var(--ink)' : 'transparent', color: active ? '#f0ede8' : 'var(--ink-3)', borderRadius: 2, cursor: 'pointer', transition: 'all 0.15s' }}>
                  {s}
                </button>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          <div style={{ flex: 1, maxWidth: 320 }}>
            <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>Min Tech Score: {minScore.toFixed(2)}</p>
            <input type="range" min={0} max={1} step={0.05} value={minScore} onChange={e => setMinScore(+e.target.value)} style={{ width: '100%', accentColor: 'var(--ink)' }} />
          </div>
          {(selTopics.length > 0 || selSources.length > 0 || minScore > 0) && (
            <button onClick={() => { setSelTopics([]); setSelSources([]); setMinScore(0) }}
              style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', padding: '4px 10px', border: '1px solid var(--accent)', color: 'var(--accent)', background: 'transparent', borderRadius: 2, cursor: 'pointer', whiteSpace: 'nowrap', alignSelf: 'flex-end', marginBottom: 2, transition: 'all 0.15s' }}>
              × Reset Filters
            </button>
          )}
        </div>

        <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)' }}>
          Showing {filtered.length} of {articles.length} articles
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.map(a => {
          const color = topicColor(a.topic)
          const pct = Math.min(100, Math.round(a.tech_score * 100))
          return (
            <div key={a.rank} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderLeft: '3px solid var(--ink)', padding: '14px 18px', transition: 'border-left-color 0.15s' }}
              onMouseEnter={e => e.currentTarget.style.borderLeftColor = 'var(--accent)'}
              onMouseLeave={e => e.currentTarget.style.borderLeftColor = 'var(--ink)'}
            >
              <div style={{ fontWeight: 500, fontSize: '0.9rem', marginBottom: 5, lineHeight: 1.4 }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', marginRight: 10 }}>#{String(a.rank).padStart(2, '0')}</span>
                <a href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', marginBottom: 6, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
                <TopicTag topic={a.topic} />
                <span>{a.source}</span>
                <span>{fmtDate(a.published_at)}</span>
                <span style={{ marginLeft: 'auto', fontWeight: 600, color: 'var(--ink)' }}>{a.tech_score.toFixed(4)}</span>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--ink-2)', lineHeight: 1.55 }}>{a.content_snippet}</div>
              <div style={{ height: 2, background: 'var(--border)', marginTop: 8 }}>
                <div style={{ height: 2, background: 'var(--ink)', width: `${pct}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}