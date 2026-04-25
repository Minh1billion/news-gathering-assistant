import { SectionRule } from './ui'
import { ClusterScatter } from './Charts'
import { topicColor } from '../lib/utils'

function ClusterCard({ cluster }) {
  const color = topicColor(cluster.topic)
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 18, height: '100%' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>Cluster {cluster.cluster_id}</div>
      <div style={{ fontSize: '0.95rem', fontWeight: 600, color, marginBottom: 10 }}>{cluster.topic}</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', display: 'flex', gap: 14, marginBottom: 12 }}>
        <span>{cluster.article_count} art.</span>
        <span>coh {cluster.cohesion_score.toFixed(3)}</span>
        <span>score {cluster.combined_score.toFixed(3)}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
        {cluster.top_keywords.slice(0, 6).map(k => (
          <span key={k.keyword} style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', background: 'var(--bg)', border: '1px solid var(--border-2)', color: 'var(--ink-2)', padding: '2px 7px', borderRadius: 2 }}>{k.keyword}</span>
        ))}
      </div>
      {cluster.top_articles.map(a => (
        <div key={a.url} style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', fontWeight: 500 }}>{a.title}</a>
          <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--ink-3)', marginTop: 3 }}>{a.source} · score {a.tech_score.toFixed(3)}</div>
        </div>
      ))}
    </div>
  )
}

export function Clusters({ clusters }) {
  const tableRows = clusters.map(c => ({
    id: `C${c.cluster_id}`, topic: c.topic,
    articles: c.article_count,
    tech: c.avg_tech_score.toFixed(3),
    cohesion: c.cohesion_score.toFixed(3),
    score: c.combined_score.toFixed(3),
    keywords: c.top_keywords.slice(0, 5).map(k => k.keyword).join(', '),
  }))

  const cols = clusters.length <= 3 ? clusters.length : clusters.length <= 6 ? 3 : 4

  return (
    <div>
      <SectionRule label="Cluster Analysis" />

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 32, marginBottom: 24 }}>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Cohesion vs Tech Score</p>
          <ClusterScatter clusters={clusters} />
        </div>
        <div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Cluster Summary</p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--mono)', fontSize: '0.72rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--ink)' }}>
                  {['ID', 'Topic', 'Art.', 'Tech', 'Coh.', 'Score', 'Keywords'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--ink-3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.62rem', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'var(--surface)' : 'var(--bg)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600 }}>{r.id}</td>
                    <td style={{ padding: '6px 10px', color: topicColor(r.topic) }}>{r.topic}</td>
                    <td style={{ padding: '6px 10px' }}>{r.articles}</td>
                    <td style={{ padding: '6px 10px' }}>{r.tech}</td>
                    <td style={{ padding: '6px 10px' }}>{r.cohesion}</td>
                    <td style={{ padding: '6px 10px', fontWeight: 600 }}>{r.score}</td>
                    <td style={{ padding: '6px 10px', color: 'var(--ink-3)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.keywords}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <p style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
        All {clusters.length} Clusters - Representative Articles
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 16 }}>
        {clusters.map(c => <ClusterCard key={c.cluster_id} cluster={c} />)}
      </div>
    </div>
  )
}