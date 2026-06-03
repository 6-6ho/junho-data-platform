import type { Card, Member, Project } from '../types'
import {
  STATUSES,
  Avatar,
  Dot,
  PriIcon,
  Due,
  Lozenge,
  keyOf,
  sortTasks,
  memberById,
} from '../lib'

interface Group {
  id: string
  head: React.ReactNode
  items: Card[]
}

function buildGroups(
  tasks: Card[],
  members: Member[],
  projects: Project[],
  group: string,
): Group[] {
  if (group === 'assignee') {
    const groups: Group[] = members.map((m) => ({
      id: m.id,
      items: tasks.filter((t) => t.assignee === m.id),
      head: (
        <>
          <Dot who={m} />
          <span
            className="col-title"
            style={{ letterSpacing: 0, textTransform: 'none', fontSize: 12, color: 'var(--text)' }}
          >
            {m.name}
          </span>
        </>
      ),
    }))
    groups.push({
      id: '__none__',
      items: tasks.filter((t) => !t.assignee),
      head: (
        <>
          <Dot who={null} />
          <span className="col-title" style={{ letterSpacing: 0, textTransform: 'none', fontSize: 12 }}>
            미할당
          </span>
        </>
      ),
    })
    return groups
  }
  if (group === 'project') {
    return projects
      .map((p) => ({
        id: p.key,
        items: tasks.filter((t) => t.project === p.key),
        head: (
          <>
            <span className="keychip">{p.key}</span>
            <span className="lg-meta">{p.label}</span>
          </>
        ),
      }))
      .filter((g) => g.items.length)
  }
  return STATUSES.map((s) => ({
    id: s.key,
    items: tasks.filter((t) => t.status === s.key),
    head: <Lozenge status={s.key} />,
  }))
}

function Row({ t, members, onOpen }: { t: Card; members: Member[]; onOpen: (id: string) => void }) {
  return (
    <div className={'row' + (t.status === 'done' ? ' is-done' : '')} onClick={() => onOpen(t.id)}>
      <span className="r-key">{keyOf(t)}</span>
      <span className="r-summary">{t.summary || '(제목 없음)'}</span>
      <span className="r-status">
        <Lozenge status={t.status} />
      </span>
      <span className="r-pri">
        <PriIcon p={t.priority} />
      </span>
      <span className="r-due">
        {t.due ? (
          <Due due={t.due} muted={t.status === 'done'} />
        ) : (
          <span className="due" style={{ color: 'var(--text-muted)' }}>
            —
          </span>
        )}
      </span>
      <span className="r-memo">
        <Avatar who={memberById(members, t.assignee)} size="sm" />
      </span>
    </div>
  )
}

export function ListView({
  tasks,
  members,
  projects,
  listGroup,
  listSort,
  onOpen,
}: {
  tasks: Card[]
  members: Member[]
  projects: Project[]
  listGroup: string
  listSort: string
  onOpen: (id: string) => void
}) {
  if (!tasks.length) return <div className="list-empty">표시할 태스크가 없습니다.</div>
  const groups = buildGroups(tasks, members, projects, listGroup)
  return (
    <div className="listview">
      {groups.map((g) =>
        g.items.length ? (
          <div className="list-group" key={g.id}>
            <div className="list-group-head">
              {g.head}
              <span className="col-count">{g.items.length}</span>
            </div>
            {sortTasks(g.items, listSort).map((t) => (
              <Row key={t.id} t={t} members={members} onOpen={onOpen} />
            ))}
          </div>
        ) : null,
      )}
    </div>
  )
}
