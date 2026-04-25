import { useRef, useState, useEffect } from 'react'
import { useReport, useHealth } from './hooks/useReport'
import { Sidebar } from './components/Sidebar'
import { ExportBar } from './components/ExportBar'
import { Clusters } from './components/Clusters'
import { Highlights } from './components/Highlights'
import { KeywordsChart, TopicBarChart, TopicPieChart, DailyChart } from './components/Charts'
import { SectionRule, MetricCard, Spinner } from './components/ui'
import { fmtDate } from './lib/utils'
import { api } from './lib/api'

function ReportHeader({ report }) {
  const s = report.stats
  return (
    <>
      <div style={{ borderBottom: '2px solid var(--ink)', paddingBottom: 16, marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--mono)', fontSize: '1.4rem', fontWeight: 600, letterSpacing: '-0.02em' }}>Weekly Tech Intelligence Report</h1>
        <p style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: 'var(--ink-3)', marginTop: 4 }}>
          Period: {report.week_start} — {report.week_end} &nbsp;·&nbsp; Generated: {fmtDate(report.generated_at)}
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 8 }}>
        <MetricCard label="Total Articles" value={s.total_tech_articles?.toLocaleString()} />
        <MetricCard label="Sources" value={s.sources} />
        <MetricCard label="Clusters" value={s.n_clusters} />
        <MetricCard label="Dominant Topic" value={s.dominant_topic} delta={`${s.dominant_topic_pct}%`} />
        <MetricCard label="Highlighted" value={report.executive_summary?.highlight_count} />
      </div>
    </>
  )
}

function ExecutiveSummary({ es, topicDistribution, dailyCounts }) {
  return (
    <div>
      <SectionRule label="Executive Summary" />

      <div style={{ background: 'var(--ink)', color: '#d4d0c8', padding: '20px 24px', lineHeight: 1.75, fontSize: '0.88rem', marginBottom: 24 }}>
        <p><strong style={{ color: '#f0ede8' }}>Overview</strong><br />{es.landscape}</p>
        <p style={{ marginTop: 16 }}>
          <strong style={{ color: '#f0ede8' }}>Dominant Topic</strong>&nbsp;&nbsp;
          {es.dominant_topic} ({es.dominant_topic_pct}%)
        </p>
        <p style={{ marginTop: 16 }}>
          <strong style={{ color: '#f0ede8' }}>Top Keywords</strong>&nbsp;&nbsp;
          {es.top_keywords.map((k, i) => (
            <span key={k}><strong style={{ color: '#f0ede8' }}>{k}</strong>{i < es.top_keywords.length - 1 ? '  ·  ' : ''}</span>
          ))}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 32 }}>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Daily Volume</p>
          <DailyChart daily={dailyCounts} />
        </div>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Topic Distribution</p>
          <TopicPieChart topics={topicDistribution} />
        </div>
      </div>
    </div>
  )
}

function KeywordsTopics({ report, onExclude, excludedCount, onReset, excludedKeywords }) {
  return (
    <div>
      <SectionRule label="Trending Keywords & Topic Distribution" />
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 32 }}>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>TF-IDF / Semantic — click keyword để ẩn</p>
          <KeywordsChart
            keywords={report.trending_keywords}
            onExclude={onExclude}
            excludedCount={excludedCount}
            excludedKeywords={excludedKeywords}
            onReset={onReset}
          />
        </div>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Articles per Topic</p>
          <TopicBarChart topics={report.topic_distribution} />
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onRun }) {
  const [running, setRunning] = useState(false)
  async function handleRun() {
    setRunning(true)
    try { await api.pipeline() } catch {}
    setRunning(false)
    onRun()
  }
  return (
    <div style={{ border: '1px dashed var(--border-2)', padding: '48px 32px', textAlign: 'center', margin: '16px 0' }}>
      <p style={{ fontFamily: 'var(--mono)', fontSize: '1rem', fontWeight: 600, marginBottom: 8 }}>◈ No report data found</p>
      <p style={{ fontSize: '0.85rem', color: 'var(--ink-3)', lineHeight: 1.6, marginBottom: 24 }}>Run the pipeline to crawl, preprocess, and generate the first report.</p>
      <button onClick={handleRun} disabled={running} style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', background: 'var(--ink)', color: '#f0ede8', border: 'none', padding: '10px 24px', cursor: running ? 'not-allowed' : 'pointer', opacity: running ? 0.6 : 1 }}>
        {running ? '⟳ Running...' : 'Run Full Pipeline'}
      </button>
    </div>
  )
}

export default function App() {
  const { ready, checking } = useHealth()
  const { report, loading, error, reload, excludedKeywords, excludeKeyword, resetExcluded } = useReport()
  const printRef = useRef(null)
  const [reports, setReports] = useState([])

  useEffect(() => {
    api.reports().then(setReports).catch(() => {})
  }, [report])

  if (checking && !ready) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <Spinner text="Connecting to API..." />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar report={report} reports={reports} onReload={reload} />

      <main className="main-content" style={{ marginLeft: 240, flex: 1, padding: '32px 40px', maxWidth: 'calc(100vw - 240px)' }}>
        {loading && <Spinner text="Loading report..." />}
        {error && <p style={{ color: 'var(--accent)', fontFamily: 'var(--mono)', fontSize: '0.8rem' }}>Error: {error}</p>}

        {!loading && !report && <EmptyState onRun={reload} />}

        {report && (
          <>
            <ReportHeader report={report} />
            <ExportBar report={report} printRef={printRef} />

            <div ref={printRef} style={{ marginTop: 16 }}>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0' }} />
              <ExecutiveSummary
                es={report.executive_summary}
                topicDistribution={report.topic_distribution}
                dailyCounts={report.daily_counts}
              />
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0' }} />
              <KeywordsTopics
                report={report}
                onExclude={excludeKeyword}
                excludedCount={excludedKeywords.size}
                onReset={resetExcluded}
                excludedKeywords={excludedKeywords}
              />
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0' }} />
              <Clusters clusters={report.clusters} />
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0' }} />
              <Highlights articles={report.highlighted_articles} />
            </div>
          </>
        )}
      </main>
    </div>
  )
}