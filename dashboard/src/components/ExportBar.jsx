import { useRef } from 'react'
import { useReactToPrint } from 'react-to-print'
import { SectionRule, Btn } from './ui'
import { downloadJson, downloadCsv } from '../lib/utils'

export function ExportBar({ report, printRef }) {
  const handlePrint = useReactToPrint({
    contentRef: printRef,
    documentTitle: `News Intelligence — ${report.week_start} to ${report.week_end}`,
    pageStyle: `
      @page { margin: 16mm 14mm; size: A4 portrait; }
      body { font-family: 'IBM Plex Sans', sans-serif; background: #fff; }
    `,
  })

  function handleJson() {
    downloadJson(report, `report_${report.week_start}_${report.week_end}.json`.replace(/\//g, '-'))
  }

  function handleCsv() {
    const rows = report.highlighted_articles.map(a => ({
      rank: a.rank, title: a.title, source: a.source,
      url: a.url, published_at: a.published_at,
      topic: a.topic, tech_score: a.tech_score,
    }))
    downloadCsv(rows, 'highlights.csv')
  }

  const btnStyle = { flex: 1, whiteSpace: 'nowrap' }

  return (
    <div className="no-print">
      <SectionRule label="Export" />
      <div style={{ display: 'flex', gap: 8, maxWidth: 480 }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--ink-3)', marginBottom: 6 }}>Report JSON</p>
          <Btn variant="primary" onClick={handleJson} style={{ ...btnStyle, width: '100%' }}>Download JSON</Btn>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--ink-3)', marginBottom: 6 }}>Highlights CSV</p>
          <Btn variant="primary" onClick={handleCsv} style={{ ...btnStyle, width: '100%' }}>Download CSV</Btn>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--ink-3)', marginBottom: 6 }}>Print / PDF</p>
          <Btn variant="primary" onClick={handlePrint} style={{ ...btnStyle, width: '100%' }}>Print / Save PDF</Btn>
        </div>
      </div>
    </div>
  )
}