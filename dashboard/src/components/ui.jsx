import { topicColor } from '../lib/utils'

export function SectionRule({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '32px 0 16px' }}>
      <span style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--ink-2)', whiteSpace: 'nowrap' }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 1, background: 'var(--border-2)' }} />
    </div>
  )
}

export function MetricCard({ label, value, delta }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderTop: '3px solid var(--ink)', padding: '18px 12px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: 110 }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--ink-2)', marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: '1.6rem', fontWeight: 600, lineHeight: 1.2 }}>{value}</div>
      {delta && <div style={{ fontFamily: 'var(--mono)', fontSize: '0.7rem', color: '#2a7a3a', marginTop: 6 }}>{delta}</div>}
    </div>
  )
}

export function Btn({ children, onClick, variant = 'default', disabled, style = {} }) {
  const base = {
    fontFamily: 'var(--mono)', fontSize: '0.72rem', fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.08em',
    border: '1px solid', borderRadius: 0, cursor: disabled ? 'not-allowed' : 'pointer',
    padding: '8px 16px', transition: 'all 0.15s', opacity: disabled ? 0.5 : 1,
    ...style,
  }
  const variants = {
    default: { background: 'transparent', color: 'var(--ink)', borderColor: 'var(--border-2)' },
    primary: { background: 'var(--ink)', color: '#f0ede8', borderColor: 'var(--ink)' },
    ghost: { background: 'transparent', color: 'var(--sidebar-text)', borderColor: 'var(--sidebar-text)' },
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{ ...base, ...variants[variant] }}
      onMouseEnter={e => {
        if (disabled) return
        if (variant === 'primary') { e.target.style.background = '#333' }
        else if (variant === 'ghost') { e.target.style.background = 'rgba(212,208,200,0.15)' }
        else { e.target.style.background = 'var(--border)' }
      }}
      onMouseLeave={e => {
        Object.assign(e.target.style, variants[variant])
      }}
    >
      {children}
    </button>
  )
}

export function TopicTag({ topic }) {
  const color = topicColor(topic)
  return (
    <span style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', padding: '2px 7px', border: `1px solid ${color}`, color, borderRadius: 2, display: 'inline-block' }}>
      {topic}
    </span>
  )
}

export function Spinner({ text = 'Loading...' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '24px 0' }}>
      <div style={{ width: 16, height: 16, border: '2px solid var(--border)', borderTopColor: 'var(--ink)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <span style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: 'var(--ink-3)' }}>{text}</span>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}