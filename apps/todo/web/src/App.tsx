import { useEffect, useRef, useState } from 'react'
import type { Activity, ActivityWho, Card, Member, Priority, Project, Status } from './types'
import { fetchBoard, saveBoard } from './api'
import { STATUSES, Svg, Avatar, keyOf, nowIso, uid, fmtDue, dueInDays } from './lib'
import { Column } from './components/Column'
import { CardModal } from './components/CardModal'
import { Subbar } from './components/Subbar'
import { ListView } from './components/ListView'

export default function App() {
  const [tasks, setTasks] = useState<Card[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [me, setMe] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filterProject, setFilterProject] = useState('all')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const firstSave = useRef(true)

  // view / theme / filters
  const [view, setView] = useState<'kanban' | 'list'>(
    () => (localStorage.getItem('kanban.view') as 'kanban' | 'list') || 'kanban',
  )
  const [theme, setTheme] = useState(() => localStorage.getItem('kanban.theme') || 'light')
  const [filterMembers, setFilterMembers] = useState<Set<string | null>>(new Set())
  const [filterPris, setFilterPris] = useState<Set<string>>(new Set())
  const [quickMine, setQuickMine] = useState(false)
  const [quickDue, setQuickDue] = useState<string | null>(null)
  const [showArchive, setShowArchive] = useState(false)
  const [listGroup, setListGroup] = useState('status')
  const [listSort, setListSort] = useState('due')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('kanban.theme', theme)
  }, [theme])
  useEffect(() => {
    localStorage.setItem('kanban.view', view)
  }, [view])

  // --- load ---
  useEffect(() => {
    fetchBoard()
      .then((d) => {
        setTasks(d.tasks || [])
        setMembers(d.members || [])
        setProjects(d.projects || [])
        setLoaded(true)
      })
      .catch((e) => {
        setErr(String(e))
        setLoaded(true)
      })
    const m = localStorage.getItem('kanban.me')
    if (m) setMe(m)
  }, [])

  // --- save (debounced, last-write-wins) ---
  useEffect(() => {
    if (!loaded) return
    if (firstSave.current) {
      firstSave.current = false
      return
    }
    const id = setTimeout(() => {
      saveBoard(tasks, me).catch((e) => setErr(String(e)))
    }, 600)
    return () => clearTimeout(id)
  }, [tasks, loaded, me])

  const meMember = members.find((m) => m.id === me) || null
  const meSnap = (): ActivityWho =>
    meMember
      ? { name: meMember.name, initial: meMember.initial, tone: meMember.tone }
      : { name: '?', initial: '?', tone: 'tx' }

  function pickMe(id: string) {
    const nid = me === id ? null : id
    setMe(nid)
    if (nid) localStorage.setItem('kanban.me', nid)
    else localStorage.removeItem('kanban.me')
  }

  function patchTask(id: string, patch: Partial<Card>, ev?: Partial<Activity>) {
    setTasks((prev) =>
      prev.map((t) => {
        if (t.id !== id) return t
        const nt: Card = { ...t, ...patch }
        if (ev) nt.activity = [...(t.activity || []), { who: meSnap(), ts: nowIso(), ...ev } as Activity]
        return nt
      }),
    )
  }

  function createTask(status: Status) {
    if (!me) {
      setErr('먼저 본인(담당자)을 선택하세요 — 우측 상단 멤버 클릭')
      return
    }
    const proj = filterProject !== 'all' ? filterProject : 'OPS'
    const nums = tasks.filter((t) => t.project === proj).map((t) => t.num)
    const num = (nums.length ? Math.max(...nums) : 0) + 1
    const t: Card = {
      id: uid(),
      project: proj,
      num,
      summary: '',
      status,
      priority: 'med',
      assignee: me,
      due: null,
      memo: '',
      archived: false,
      activity: [{ type: 'created', who: meSnap(), ts: nowIso() }],
    }
    setTasks((prev) => [t, ...prev])
    setEditingId(t.id)
  }

  function deleteTask(id: string) {
    if (!confirm('이 카드를 삭제할까요?')) return
    setTasks((prev) => prev.filter((t) => t.id !== id))
    setEditingId(null)
  }

  function addComment(id: string, text: string) {
    patchTask(id, {}, { type: 'comment', text })
  }

  function onMove(id: string, status: Status, beforeId: string | null) {
    setTasks((prev) => {
      const t = prev.find((x) => x.id === id)
      if (!t) return prev
      const changed = t.status !== status
      const nt: Card = changed
        ? {
            ...t,
            status,
            activity: [
              ...(t.activity || []),
              { type: 'status', who: meSnap(), ts: nowIso(), from: t.status, to: status } as Activity,
            ],
          }
        : t
      const rest = prev.filter((x) => x.id !== id)
      if (beforeId) {
        const i = rest.findIndex((x) => x.id === beforeId)
        if (i >= 0) rest.splice(i, 0, nt)
        else rest.push(nt)
      } else {
        rest.push(nt)
      }
      return rest
    })
  }

  function togglePri(p: Priority) {
    setFilterPris((prev) => {
      const n = new Set(prev)
      if (n.has(p)) n.delete(p)
      else n.add(p)
      return n
    })
  }
  function toggleMember(id: string) {
    setFilterMembers((prev) => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }
  function clearFilters() {
    setQuickMine(false)
    setQuickDue(null)
    setFilterPris(new Set())
    setFilterMembers(new Set())
    setFilterProject('all')
  }

  // --- visible (full filter chain) ---
  const q = search.trim().toLowerCase()
  const myId = me || '__me__'
  const visible = tasks.filter((t) => {
    if (showArchive ? !t.archived : t.archived) return false
    if (filterProject !== 'all' && t.project !== filterProject) return false
    if (filterMembers.size && !filterMembers.has(t.assignee)) return false
    if (quickMine && t.assignee !== myId) return false
    if (filterPris.size && !filterPris.has(t.priority || '')) return false
    if (quickDue === 'over') {
      const f = fmtDue(t.due)
      if (!(f && f.st === 'over' && t.status !== 'done')) return false
    }
    if (quickDue === 'week') {
      const d = dueInDays(t.due)
      if (!(d !== null && d >= 0 && d <= 7 && t.status !== 'done')) return false
    }
    if (q) {
      const hay = `${keyOf(t)} ${t.summary} ${t.memo || ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })

  const editing = tasks.find((t) => t.id === editingId) || null
  const doneCount = tasks.filter((t) => t.status === 'done' && !t.archived).length
  const activeCount = tasks.filter((t) => t.status !== 'done' && !t.archived).length

  return (
    <div className="app">
      <header className="topbar" style={topbarStyle}>
        <span className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="brand-mark">칸</span>
          <span className="brand-name">
            칸반보드 <span className="dim">/ 공유</span>
          </span>
        </span>

        <div style={{ position: 'relative', flex: '0 1 220px' }}>
          <span style={{ position: 'absolute', left: 8, top: 7, opacity: 0.5 }}>
            <Svg name="search" />
          </span>
          <input
            value={search}
            placeholder="검색"
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: '100%', paddingLeft: 28 }}
          />
        </div>

        <select value={filterProject} onChange={(e) => setFilterProject(e.target.value)}>
          <option value="all">전체 프로젝트</option>
          {projects.map((p) => (
            <option key={p.key} value={p.key}>
              {p.key} · {p.label}
            </option>
          ))}
        </select>

        <span style={{ flex: 1 }} />

        {/* view toggle */}
        <div className="seg" style={{ display: 'flex', gap: 2 }}>
          <button
            className={'btn icon ghost' + (view === 'kanban' ? ' active-toggle' : '')}
            title="칸반"
            onClick={() => setView('kanban')}
            style={view === 'kanban' ? activeBtn : undefined}
          >
            <Svg name="kanban" />
          </button>
          <button
            className={'btn icon ghost' + (view === 'list' ? ' active-toggle' : '')}
            title="리스트"
            onClick={() => setView('list')}
            style={view === 'list' ? activeBtn : undefined}
          >
            <Svg name="list" />
          </button>
        </div>

        <button
          className={'btn icon ghost' + (showArchive ? ' active-toggle' : '')}
          title={showArchive ? '활성 보기' : '아카이브 보기'}
          onClick={() => setShowArchive((v) => !v)}
          style={showArchive ? activeBtn : undefined}
        >
          <Svg name="archive" />
        </button>
        <button
          className="btn icon ghost"
          title="테마"
          onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
        >
          <Svg name="theme" />
        </button>

        <span style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 4 }}>
          {members.map((m) => (
            <button
              key={m.id}
              onClick={() => pickMe(m.id)}
              title={me === m.id ? `${m.name} (나)` : `${m.name} 로 지정`}
              style={{
                border: me === m.id ? '2px solid var(--accent)' : '2px solid transparent',
                borderRadius: '50%',
                padding: 0,
                background: 'none',
                cursor: 'pointer',
              }}
            >
              <Avatar who={m} size="sm" />
            </button>
          ))}
        </span>
      </header>

      <Subbar
        me={me}
        members={members}
        quickMine={quickMine}
        toggleMine={() => setQuickMine((v) => !v)}
        quickDue={quickDue}
        setQuickDue={setQuickDue}
        filterPris={filterPris}
        togglePri={togglePri}
        filterMembers={filterMembers}
        toggleMember={toggleMember}
        filterProject={filterProject}
        clearFilters={clearFilters}
        view={view}
        listGroup={listGroup}
        setListGroup={setListGroup}
        listSort={listSort}
        setListSort={setListSort}
        count={visible.length}
      />

      {err && (
        <div
          style={{ background: 'var(--accent-subtle)', color: 'var(--pri-high)', padding: '6px 16px', fontSize: 13, cursor: 'pointer' }}
          onClick={() => setErr(null)}
        >
          {err} (클릭하여 닫기)
        </div>
      )}

      <div className="board-wrap" style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {!loaded ? (
          <div style={{ padding: 40, color: 'var(--text-muted)' }}>불러오는 중…</div>
        ) : view === 'kanban' ? (
          <div className="kanban" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            {STATUSES.map((col) => (
              <Column
                key={col.key}
                col={col}
                items={visible.filter((t) => t.status === col.key)}
                members={members}
                onCreate={createTask}
                onOpen={setEditingId}
                onMove={onMove}
              />
            ))}
          </div>
        ) : (
          <ListView
            tasks={visible}
            members={members}
            projects={projects}
            listGroup={listGroup}
            listSort={listSort}
            onOpen={setEditingId}
          />
        )}
      </div>

      <footer className="statusbar" style={statusbarStyle}>
        <span>진행 {activeCount}</span>
        <span>완료 {doneCount}</span>
        <span style={{ flex: 1 }} />
        <span>{meMember ? `${meMember.name} 으로 작업 중` : '본인 미선택'}</span>
      </footer>

      {editing && (
        <CardModal
          t={editing}
          members={members}
          projects={projects}
          me={me}
          onPatch={patchTask}
          onDelete={deleteTask}
          onClose={() => setEditingId(null)}
          onComment={addComment}
        />
      )}
    </div>
  )
}

const topbarStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '8px 16px',
  borderBottom: '1px solid var(--border)',
  background: 'var(--surface)',
}
const statusbarStyle: React.CSSProperties = {
  padding: '6px 16px',
  borderTop: '1px solid var(--border)',
  fontSize: 12,
  color: 'var(--text-muted)',
  display: 'flex',
  gap: 14,
}
const activeBtn: React.CSSProperties = { color: 'var(--accent)', background: 'var(--accent-subtle)' }
