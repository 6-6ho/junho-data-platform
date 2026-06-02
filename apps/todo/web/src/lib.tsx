import type { Card, Member, Priority, Status } from './types'

export const STATUSES: { key: Status; label: string }[] = [
  { key: 'todo', label: 'TO DO' },
  { key: 'doing', label: 'IN PROGRESS' },
  { key: 'done', label: 'DONE' },
]
export const PRIORITIES: { key: Priority; label: string }[] = [
  { key: 'high', label: '높음' },
  { key: 'med', label: '보통' },
  { key: 'low', label: '낮음' },
]
export const PRI_RANK: Record<string, number> = { high: 0, med: 1, low: 2 }
export const PRI_LABEL: Record<string, string> = { high: '높음', med: '보통', low: '낮음' }
export const COL_TONE: Record<Status, string> = {
  todo: 'var(--st-todo-fg)',
  doing: 'var(--accent)',
  done: 'var(--st-done-fg)',
}

export const uid = () => 't' + Math.random().toString(36).slice(2, 9)
export const keyOf = (t: Card) => `${t.project}-${t.num}`
export const commentCount = (t: Card) => (t.activity || []).filter((a) => a.type === 'comment').length
export const nowIso = () => new Date().toISOString()

const TODAY = new Date(new Date().toISOString().slice(0, 10) + 'T00:00:00')

export function fmtDue(due: string | null) {
  if (!due) return null
  const d = new Date(due + 'T00:00:00')
  const diff = Math.round((d.getTime() - TODAY.getTime()) / 86400000)
  const md = `${d.getMonth() + 1}/${d.getDate()}`
  let st = '', label = md, full = md, pill = false
  if (diff < 0) { st = 'over'; full = `${md} · ${-diff}일 지남`; pill = true }
  else if (diff === 0) { st = 'today'; label = '오늘'; full = '오늘 마감'; pill = true }
  else if (diff <= 3) { st = 'soon'; full = `${md} · ${diff}일 남음` }
  return { st, label, short: md, full, pill }
}

export function relTime(ts: string): string {
  const t = new Date(ts)
  const s = Math.round((Date.now() - t.getTime()) / 1000)
  if (s < 60) return '방금'
  if (s < 3600) return `${Math.floor(s / 60)}분 전`
  if (s < 86400) return `${Math.floor(s / 3600)}시간 전`
  if (s < 86400 * 7) return `${Math.floor(s / 86400)}일 전`
  return `${t.getMonth() + 1}월 ${t.getDate()}일`
}

export const ICONS: Record<string, string> = {
  kanban: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2" y="2.5" width="3.4" height="11" rx="1"/><rect x="6.4" y="2.5" width="3.4" height="8" rx="1"/><rect x="10.8" y="2.5" width="3.4" height="6" rx="1"/></svg>',
  list: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M3 4.5h10M3 8h10M3 11.5h10"/></svg>',
  search: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="7" cy="7" r="4.2"/><path d="M10.2 10.2 13.5 13.5" stroke-linecap="round"/></svg>',
  plus: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M8 3.5v9M3.5 8h9"/></svg>',
  archive: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2.5" y="3" width="11" height="3" rx="1"/><path d="M3.5 6.5v6a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1v-6M6.5 9h3"/></svg>',
  theme: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M13 8.6A5 5 0 1 1 7.4 3a4 4 0 0 0 5.6 5.6z" fill="currentColor" fill-opacity=".15"/></svg>',
  activity: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 8.5h3L6 4l3 9 1.6-4.5H14.5"/></svg>',
  cal: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><rect x="2.5" y="3.5" width="11" height="10" rx="1.5"/><path d="M2.5 6.5h11M5.5 2.2v2.4M10.5 2.2v2.4" stroke-linecap="round"/></svg>',
  memo: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M4 4h8M4 7h8M4 10h5"/></svg>',
  comment: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4.2A1.2 1.2 0 0 1 4.2 3h7.6A1.2 1.2 0 0 1 13 4.2v5A1.2 1.2 0 0 1 11.8 10.4H6.5L3.8 12.8V10.4H4.2A1.2 1.2 0 0 1 3 9.2z"/></svg>',
  close: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
  trash: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M3 4.5h10M6.5 4V3h3v1M5 4.5l.6 8h4.8l.6-8"/></svg>',
  ev_new: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 4v8M4 8h8"/></svg>',
  ev_status: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 8h10M9 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  ev_person: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="8" cy="6" r="2.4"/><path d="M3.8 12.5a4.2 4.2 0 0 1 8.4 0"/></svg>',
  ev_flag: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M4 13V3M4 3.5h7l-1.4 2.2L11 8H4"/></svg>',
  ev_cal: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><rect x="3" y="4" width="10" height="9" rx="1.5"/><path d="M3 6.6h10" stroke-linecap="round"/></svg>',
  ev_edit: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M10.5 3.5l2 2L6 12l-2.6.6L4 10z"/></svg>',
}

export function Svg({ name, className }: { name: string; className?: string }) {
  return <span className={className} dangerouslySetInnerHTML={{ __html: ICONS[name] || '' }} />
}

export function PriIcon({ p }: { p: Priority | null }) {
  if (!p) return null
  const paths: Record<string, string> = {
    high: '<path d="M4 10l4-4 4 4" />',
    med: '<path d="M4 6.4h8M4 9.6h8" />',
    low: '<path d="M4 6l4 4 4-4" />',
  }
  const svg = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[p]}</svg>`
  return <span className={`pri ${p}`} title={`우선순위 ${PRI_LABEL[p]}`} dangerouslySetInnerHTML={{ __html: svg }} />
}

type WhoLike = { name: string; initial?: string; tone?: string } | null
export function Avatar({ who, size }: { who: WhoLike; size?: string }) {
  const cls = size ? ` ${size}` : ''
  if (!who) return <span className={`avatar unassigned${cls}`} title="미할당">–</span>
  return (
    <span className={`avatar ${who.tone || 'tx'}${cls}`} title={who.name}>
      {who.initial || (who.name || '?')[0]}
    </span>
  )
}

export function Lozenge({ status }: { status: Status }) {
  const s = STATUSES.find((x) => x.key === status)
  return <span className={`lozenge ${status}`}>{s ? s.label : status}</span>
}

export function Due({ due, muted }: { due: string | null; muted?: boolean }) {
  const f = fmtDue(due)
  if (!f) return null
  if (muted) {
    return (
      <span className="due" style={{ color: 'var(--text-muted)', fontWeight: 500 }} title={f.full}>
        <Svg name="cal" />
        <span>{f.short}</span>
      </span>
    )
  }
  return (
    <span className={`due ${f.st}${f.pill ? ' pill' : ''}`} title={f.full}>
      {!f.pill && <Svg name="cal" />}
      <span>{f.label}</span>
    </span>
  )
}

export const memberById = (members: Member[], id: string | null) =>
  members.find((m) => m.id === id) || null

export function createdTs(t: Card): number {
  const c = (t.activity || []).find((a) => a.type === 'created')
  return c ? new Date(c.ts).getTime() : 0
}

export function dueInDays(due: string | null): number | null {
  if (!due) return null
  return Math.round((new Date(due + 'T00:00:00').getTime() - TODAY.getTime()) / 86400000)
}

export function sortTasks(arr: Card[], mode: string): Card[] {
  const byDue = (a: Card, b: Card) => {
    const da = a.due ? new Date(a.due).getTime() : Infinity
    const db = b.due ? new Date(b.due).getTime() : Infinity
    return da - db
  }
  const cp = arr.slice()
  if (mode === 'due') cp.sort(byDue)
  else if (mode === 'priority')
    cp.sort(
      (a, b) =>
        ((PRI_RANK[a.priority || ''] ?? 9) - (PRI_RANK[b.priority || ''] ?? 9)) || byDue(a, b),
    )
  else if (mode === 'created') cp.sort((a, b) => createdTs(b) - createdTs(a))
  return cp
}
