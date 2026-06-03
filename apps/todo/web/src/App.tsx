import { useEffect, useRef, useState } from 'react'
import type { Activity, ActivityWho, Card, Member, Priority, Project, Status } from './types'
import { fetchBoard, saveBoard, saveProjects } from './api'
import { STATUSES, Svg, keyOf, nowIso, uid, fmtDue, dueInDays } from './lib'
import { Column } from './components/Column'
import { CardModal } from './components/CardModal'
import { Subbar } from './components/Subbar'
import { ListView } from './components/ListView'
import { CalendarView } from './components/CalendarView'
import { ProjectManager } from './components/ProjectManager'

export default function App() {
  const [tasks, setTasks] = useState<Card[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [me, setMe] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filterProject, setFilterProject] = useState('all')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [creating, setCreating] = useState<Card | null>(null) // 미커밋 새 카드 초안
  const [showProjMgr, setShowProjMgr] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const firstSave = useRef(true)
  const rev = useRef(0) // 서버 보드 버전 (낙관적 잠금)
  const dirty = useRef(false) // 내 미저장 변경 있음 → 폴링이 덮어쓰지 않게
  const applyingRemote = useRef(false) // 서버 상태 수용 중 → 되-저장(echo) 방지

  // view / theme / filters
  const [view, setView] = useState<'kanban' | 'list' | 'calendar'>(
    () => (localStorage.getItem('kanban.view') as 'kanban' | 'list' | 'calendar') || 'kanban',
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
        rev.current = d.rev || 0
        setLoaded(true)
      })
      .catch((e) => {
        setErr(String(e))
        setLoaded(true)
      })
    const m = localStorage.getItem('kanban.me')
    if (m) setMe(m)
  }, [])

  // --- save (debounced, 낙관적 잠금 rev) ---
  useEffect(() => {
    if (!loaded) return
    if (firstSave.current) {
      firstSave.current = false
      return
    }
    // 폴링/충돌로 서버 상태를 받아 적용한 turn 이면 되-저장하지 않는다 (echo 방지)
    if (applyingRemote.current) {
      applyingRemote.current = false
      return
    }
    dirty.current = true
    const id = setTimeout(async () => {
      try {
        const res = await saveBoard(tasks, rev.current, me)
        if (res.ok) {
          rev.current = res.rev
          dirty.current = false
        } else {
          // 다른 사람이 먼저 저장 → 최신본 수용 (내 미저장 변경은 덮임 → 토스트로 알림)
          applyingRemote.current = true
          rev.current = res.rev
          dirty.current = false
          setTasks(res.tasks)
          setErr('다른 사람이 먼저 저장해서 최신본으로 갱신했어요. 방금 변경은 다시 확인하세요.')
        }
      } catch (e) {
        setErr(String(e))
      }
    }, 600)
    return () => clearTimeout(id)
  }, [tasks, loaded, me])

  // --- 라이브 동기화: 5초마다 서버 rev 확인. 내 미저장 변경/카드 편집 중이 아니면 최신본 반영 ---
  useEffect(() => {
    if (!loaded) return
    const id = setInterval(async () => {
      if (dirty.current || editingId) return
      try {
        const d = await fetchBoard()
        if ((d.rev || 0) !== rev.current) {
          applyingRemote.current = true
          rev.current = d.rev || 0
          setTasks(d.tasks || [])
          setMembers(d.members || [])
          setProjects(d.projects || [])
        }
      } catch {
        /* 폴링 실패는 조용히 무시 */
      }
    }, 5000)
    return () => clearInterval(id)
  }, [loaded, editingId])

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

  // 만들기 → 초안 모달만 띄운다 (확인=생성 누르기 전엔 보드/서버에 안 들어감)
  function startCreate(status: Status) {
    if (!me) {
      setErr('먼저 본인(담당자)을 선택하세요 — 우측 상단 "나는" 에서 선택')
      return
    }
    const proj = filterProject !== 'all' ? filterProject : projects[0]?.key || 'OPS'
    setCreating({
      id: uid(),
      project: proj,
      num: 0, // 생성 확정 시점에 프로젝트 기준으로 다시 매김
      summary: '',
      status,
      priority: 'med',
      assignee: me,
      due: null,
      memo: '',
      archived: false,
      activity: [{ type: 'created', who: meSnap(), ts: nowIso() }],
    })
  }

  function patchCreating(patch: Partial<Card>) {
    setCreating((c) => (c ? { ...c, ...patch } : c))
  }

  // 생성 확인 → 이때 비로소 보드에 추가 (프로젝트 기준 번호 부여)
  function commitCreate() {
    if (!creating) return
    const proj = creating.project
    const nums = tasks.filter((t) => t.project === proj).map((t) => t.num)
    const num = (nums.length ? Math.max(...nums) : 0) + 1
    setTasks((prev) => [{ ...creating, num }, ...prev])
    setCreating(null)
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
      <header className="topbar">
        <span className="brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="brand-name">성북반상회</span>
        </span>

        <div className="search">
          <Svg name="search" />
          <input value={search} placeholder="검색" onChange={(e) => setSearch(e.target.value)} />
        </div>

        <select className="filter-select" value={filterProject} onChange={(e) => setFilterProject(e.target.value)}>
          <option value="all">전체 프로젝트</option>
          {projects.map((p) => (
            <option key={p.key} value={p.key}>
              {p.key} · {p.label}
            </option>
          ))}
        </select>
        <button
          className="btn icon ghost"
          title="프로젝트 관리"
          onClick={() => setShowProjMgr(true)}
        >
          <Svg name="gear" />
        </button>

        <span style={{ flex: 1 }} />

        {/* view toggle */}
        <div className="seg">
          <button
            className={view === 'kanban' ? 'active' : ''}
            title="칸반"
            onClick={() => setView('kanban')}
          >
            <Svg name="kanban" />
          </button>
          <button
            className={view === 'list' ? 'active' : ''}
            title="리스트"
            onClick={() => setView('list')}
          >
            <Svg name="list" />
          </button>
          <button
            className={view === 'calendar' ? 'active' : ''}
            title="달력"
            onClick={() => setView('calendar')}
          >
            <Svg name="cal" />
          </button>
        </div>

        <button
          className={'btn icon ghost' + (showArchive ? ' active-toggle' : '')}
          title={showArchive ? '활성 보기' : '아카이브 보기'}
          onClick={() => setShowArchive((v) => !v)}
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

        <span className="me-picker" title="나로 지정 — 카드 담당자·작성자에 쓰임">
          <span className="me-picker-label">나는</span>
          {members.map((m) => (
            <button
              key={m.id}
              className={'me-opt' + (me === m.id ? ' on' : '')}
              onClick={() => pickMe(m.id)}
              title={me === m.id ? `${m.name} (나) — 클릭 시 해제` : `${m.name} 로 지정`}
            >
              <span className="me-opt-name">{m.name}</span>
              {me === m.id && <Svg name="check" className="me-opt-check" />}
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

      <div className="board-wrap">
        {!loaded ? (
          <div style={{ padding: 40, color: 'var(--text-muted)' }}>불러오는 중…</div>
        ) : view === 'kanban' ? (
          <div className="kanban">
            {STATUSES.map((col) => (
              <Column
                key={col.key}
                col={col}
                items={visible.filter((t) => t.status === col.key)}
                members={members}
                onCreate={startCreate}
                onOpen={setEditingId}
                onMove={onMove}
              />
            ))}
          </div>
        ) : view === 'list' ? (
          <ListView
            tasks={visible}
            members={members}
            projects={projects}
            listGroup={listGroup}
            listSort={listSort}
            onOpen={setEditingId}
          />
        ) : (
          <CalendarView tasks={visible} onOpen={setEditingId} me={me} />
        )}
      </div>

      <footer className="statusbar">
        <span>진행 {activeCount}</span>
        <span>완료 {doneCount}</span>
        <span style={{ flex: 1 }} />
        <span>{meMember ? `${meMember.name} 으로 작업 중` : '본인 미선택'}</span>
      </footer>

      {showProjMgr && (
        <ProjectManager
          projects={projects}
          onSave={async (list) => {
            const saved = await saveProjects(list, me)
            setProjects(saved)
          }}
          onClose={() => setShowProjMgr(false)}
        />
      )}

      {creating && (
        <CardModal
          t={creating}
          mode="create"
          members={members}
          projects={projects}
          me={me}
          onChange={patchCreating}
          onPrimary={commitCreate}
          onCancel={() => setCreating(null)}
        />
      )}

      {editing && (
        <CardModal
          t={editing}
          mode="edit"
          members={members}
          projects={projects}
          me={me}
          onChange={(patch, ev) => patchTask(editing.id, patch, ev)}
          onCancel={() => setEditingId(null)}
          onDelete={() => deleteTask(editing.id)}
          onComment={(text) => addComment(editing.id, text)}
        />
      )}
    </div>
  )
}

