import type { Member, Priority } from '../types'
import { PRIORITIES, Avatar, Dot, PriIcon } from '../lib'

export function Subbar({
  me,
  members,
  quickMine,
  toggleMine,
  quickDue,
  setQuickDue,
  filterPris,
  togglePri,
  filterMembers,
  toggleMember,
  filterProject,
  clearFilters,
  view,
  listGroup,
  setListGroup,
  listSort,
  setListSort,
  count,
}: {
  me: string | null
  members: Member[]
  quickMine: boolean
  toggleMine: () => void
  quickDue: string | null
  setQuickDue: (v: string | null) => void
  filterPris: Set<string>
  togglePri: (p: Priority) => void
  filterMembers: Set<string | null>
  toggleMember: (id: string) => void
  filterProject: string
  clearFilters: () => void
  view: string
  listGroup: string
  setListGroup: (v: string) => void
  listSort: string
  setListSort: (v: string) => void
  count: number
}) {
  const meMember = members.find((m) => m.id === me) || { name: '?', initial: '?', tone: 'tx' }
  const anyActive =
    quickMine || !!quickDue || filterPris.size > 0 || filterMembers.size > 0 || filterProject !== 'all'

  return (
    <div
      className="subbar"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 16px',
        borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap',
        fontSize: 12,
      }}
    >
      <span className="sub-label" style={{ color: 'var(--text-muted)' }}>
        빠른 필터
      </span>

      <button className={'chip' + (quickMine ? ' on' : '')} onClick={toggleMine}>
        <Avatar who={meMember} size="sm" />
        <span>내 작업</span>
      </button>
      <button
        className={'chip' + (quickDue === 'over' ? ' on' : '')}
        onClick={() => setQuickDue(quickDue === 'over' ? null : 'over')}
      >
        <span className="cdot" style={{ background: 'var(--due-over)' }} />
        지연
      </button>
      <button
        className={'chip' + (quickDue === 'week' ? ' on' : '')}
        onClick={() => setQuickDue(quickDue === 'week' ? null : 'week')}
      >
        <span className="cdot" style={{ background: 'var(--due-today)' }} />
        이번 주
      </button>

      <div className="vrule" />

      {PRIORITIES.map((p) => {
        const on = filterPris.has(p.key)
        return (
          <button key={p.key} className={'chip' + (on ? ' on' : '')} onClick={() => togglePri(p.key)}>
            <PriIcon p={p.key} />
            <span>{p.label}</span>
          </button>
        )
      })}

      {members.length > 0 && <div className="vrule" />}
      {members.map((m) => {
        const on = filterMembers.has(m.id)
        return (
          <button key={m.id} className={'chip' + (on ? ' on' : '')} onClick={() => toggleMember(m.id)}>
            <Dot who={m} />
            <span>{m.name}</span>
          </button>
        )
      })}

      {anyActive && (
        <button className="chip clear" onClick={clearFilters}>
          필터 초기화 ✕
        </button>
      )}

      {view === 'list' && (
        <>
          <div className="vrule" />
          <span className="sub-label" style={{ color: 'var(--text-muted)' }}>
            그룹
          </span>
          <select className="sub-select" value={listGroup} onChange={(e) => setListGroup(e.target.value)}>
            <option value="status">상태</option>
            <option value="assignee">담당자</option>
            <option value="project">프로젝트</option>
          </select>
          <span className="sub-label" style={{ color: 'var(--text-muted)' }}>
            정렬
          </span>
          <select className="sub-select" value={listSort} onChange={(e) => setListSort(e.target.value)}>
            <option value="due">마감일순</option>
            <option value="priority">우선순위순</option>
            <option value="created">생성순</option>
          </select>
        </>
      )}

      <span style={{ flex: 1 }} />
      <span className="result-count" style={{ color: 'var(--text-muted)' }}>
        {count}건
      </span>
    </div>
  )
}
