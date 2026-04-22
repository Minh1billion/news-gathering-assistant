import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  Area, AreaChart,
  ScatterChart, Scatter, ZAxis,
  ResponsiveContainer, Cell,
} from 'recharts'
import { topicColor } from '../lib/utils'

const MONO = 'IBM Plex Mono, monospace'
const axisStyle = { fontFamily: MONO, fontSize: 10, fill: '#5a5855' }
const tooltipStyle = { fontFamily: MONO, fontSize: 11, background: '#fff', border: '1px solid #e0ddd6', borderRadius: 0 }

function ExcludableYTick({ x, y, payload, onExclude }) {
  const [hovered, setHovered] = useState(false)
  return (
    <g transform={`translate(${x},${y})`}>
      <rect
        x={-76} y={-9} width={76} height={18}
        fill="transparent"
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => onExclude(payload.value)}
      />
      <text
        x={-4} y={0}
        textAnchor="end"
        dominantBaseline="central"
        style={{ fontFamily: MONO, fontSize: 10, fill: hovered ? '#c0392b' : '#5a5855', pointerEvents: 'none' }}
      >
        {hovered ? `✕ ${payload.value}` : payload.value}
      </text>
    </g>
  )
}

export function KeywordsChart({ keywords, onExclude, excludedCount, onReset, excludedKeywords = new Set() }) {
  const data = [...keywords]
    .filter(k => !excludedKeywords.has(k.keyword))
    .sort((a, b) => b.combined_score - a.combined_score)
    .slice(0, 15)
    .sort((a, b) => a.combined_score - b.combined_score)

  const barHeight = 28
  const chartHeight = data.length * barHeight + 40

  return (
    <div>
      {excludedCount > 0 && (
        <div style={{ fontFamily: MONO, fontSize: 10, color: '#888', marginBottom: 6, textAlign: 'right' }}>
          {excludedCount} keyword ẩn —{' '}
          <span onClick={onReset} style={{ color: '#c0392b', cursor: 'pointer', textDecoration: 'underline' }}>
            reset
          </span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20, top: 8, bottom: 8 }}>
          <XAxis type="number" tick={axisStyle} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="keyword"
            axisLine={false}
            tickLine={false}
            width={80}
            tick={onExclude
              ? (props) => <ExcludableYTick {...props} onExclude={onExclude} />
              : axisStyle
            }
          />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontFamily: MONO, fontSize: 10 }} />
          <Bar dataKey="tfidf_score" name="TF-IDF" fill="#2c3e50" opacity={0.9} radius={0} barSize={10} />
          <Bar dataKey="semantic_score" name="Semantic" fill="#95a5a6" opacity={0.7} radius={0} barSize={10} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function TopicBarChart({ topics }) {
  const data = [...topics].sort((a, b) => a.count - b.count)
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 100, right: 40, top: 8, bottom: 8 }}>
        <XAxis type="number" tick={axisStyle} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="topic" tick={axisStyle} axisLine={false} tickLine={false} width={100} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v, n, p) => [`${v} (${p.payload.percentage}%)`, 'Articles']} />
        <Bar dataKey="count" radius={0}>
          {data.map(d => <Cell key={d.topic} fill={topicColor(d.topic)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function DailyChart({ daily }) {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={daily} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2c3e50" stopOpacity={0.12} />
            <stop offset="95%" stopColor="#2c3e50" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" tick={axisStyle} axisLine={false} tickLine={false} tickFormatter={d => d.slice(5)} />
        <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={28} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area type="monotone" dataKey="count" stroke="#2c3e50" strokeWidth={1.5} fill="url(#areaGrad)" dot={{ r: 3, fill: '#2c3e50' }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ClusterScatter({ clusters }) {
  const data = clusters.map(c => ({
    x: c.cohesion_score,
    y: c.avg_tech_score,
    z: c.article_count,
    label: `C${c.cluster_id}`,
    topic: c.topic,
    id: c.cluster_id,
  }))

  const xVals = data.map(d => d.x)
  const yVals = data.map(d => d.y)
  const pad = (arr, ratio = 0.15) => {
    const mn = Math.min(...arr), mx = Math.max(...arr), r = (mx - mn) || 0.1
    return [+(mn - r * ratio).toFixed(3), +(mx + r * ratio).toFixed(3)]
  }

  const CustomDot = (props) => {
    const { cx, cy, payload } = props
    const r = Math.max(8, Math.sqrt(payload.z) * 3)
    return (
      <g>
        <circle cx={cx} cy={cy} r={r} fill={topicColor(payload.topic)} opacity={0.85} stroke="#fff" strokeWidth={1.5} />
        <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" style={{ fontFamily: MONO, fontSize: 9, fill: '#fff', fontWeight: 600, pointerEvents: 'none' }}>
          {payload.label}
        </text>
      </g>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ left: 20, right: 20, top: 16, bottom: 32 }}>
        <XAxis
          dataKey="x" type="number" name="Cohesion"
          domain={pad(xVals)} tick={axisStyle} axisLine={false} tickLine={false}
          tickFormatter={v => v.toFixed(3)}
          label={{ value: 'Cohesion', position: 'insideBottom', offset: -16, style: axisStyle }}
        />
        <YAxis
          dataKey="y" type="number" name="Tech Score"
          domain={pad(yVals)} tick={axisStyle} axisLine={false} tickLine={false}
          tickFormatter={v => v.toFixed(2)}
          label={{ value: 'Tech Score', angle: -90, position: 'insideLeft', offset: 10, style: axisStyle }}
          width={44}
        />
        <ZAxis dataKey="z" range={[1, 1]} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ strokeDasharray: '3 3', stroke: '#c8c5be' }}
          content={({ payload }) => {
            if (!payload?.length) return null
            const d = payload[0]?.payload
            return (
              <div style={{ ...tooltipStyle, padding: '8px 12px' }}>
                <p style={{ fontWeight: 600, marginBottom: 4 }}>{d?.label} — {d?.topic}</p>
                <p>Cohesion: {d?.x?.toFixed(4)}</p>
                <p>Tech score: {d?.y?.toFixed(4)}</p>
                <p>Articles: {d?.z}</p>
              </div>
            )
          }}
        />
        <Scatter data={data} shape={<CustomDot />} />
      </ScatterChart>
    </ResponsiveContainer>
  )
}