export const TOPIC_COLORS = {
  'AI / ML': '#3498db',
  'Phần mềm / Dev': '#5dade2',
  'Phan mem / Dev': '#5dade2',
  'Thiết bị di động': '#e67e22',
  'Thiet bi di dong': '#e67e22',
  'An ninh mạng': '#e74c3c',
  'An ninh mang': '#e74c3c',
  'Phần cứng / Server': '#2ecc71',
  'Phan cung / Server': '#2ecc71',
  'Startup / Đầu tư': '#9b59b6',
  'Startup / Dau tu': '#9b59b6',
  'Crypto / Blockchain': '#f1c40f',
  'Xe điện / Năng lượng': '#1abc9c',
  'Xe dien / Nang luong': '#1abc9c',
}

export function topicColor(t) {
  return TOPIC_COLORS[t] ?? '#7f8c8d'
}

export function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString('vi-VN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function downloadCsv(rows, filename) {
  if (!rows.length) return
  const keys = Object.keys(rows[0])
  const csv = [keys.join(','), ...rows.map(r => keys.map(k => JSON.stringify(r[k] ?? '')).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}