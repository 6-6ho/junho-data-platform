import { useState } from 'react'
import type { Activity, Card, Member, Project } from '../types'
import {
  Avatar,
  PriIcon,
  Svg,
  Lozenge,
  STATUSES,
  PRIORITIES,
  PRI_LABEL,
  keyOf,
  relTime,
} from '../lib'

export function CardModal({
  t,
  members,
  projects,
  me,
  onPatch,
  onDelete,
  onClose,
  onComment,
}: {
  t: Card
  members: Member[]
  projects: Project[]
  me: string | null
  onPatch: (id: string, patch: Partial<Card>, ev?: Partial<Activity>) => void
  onDelete: (id: string) => void
  onClose: () => void
  onComment: (id: string, text: string) => void
}) {
  const [tab, setTab] = useState<'all' | 'comment' | 'event'>('all')
  const [comment, setComment] = useState('')
  const meMember = members.find((m) => m.id === me) || { name: '게스트', initial: '?', tone: 'tx' }

  const acts = [...(t.activity || [])].sort(
    (a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime(),
  )
  const comments = acts.filter((a) => a.type === 'comment')
  const shown = acts.filter((a) =>
    tab === 'all' ? true : tab === 'comment' ? a.type === 'comment' : a.type !== 'comment',
  )

  function submit() {
    const v = comment.trim()
    if (!v) return
    onComment(t.id, v)
    setComment('')
  }

  return (
    <div
      className="overlay open"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '48px 16px',
        zIndex: 50,
        overflow: 'auto',
      }}
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="keychip">{keyOf(t)}</span>
          <select
            className="filter-select"
            style={{ fontSize: 11 }}
            value={t.project}
            onChange={(e) => onPatch(t.id, { project: e.target.value }, { type: 'edit', field: 'project' })}
          >
            {!projects.some((p) => p.key === t.project) && <option value={t.project}>{t.project}</option>}
            {projects.map((p) => (
              <option key={p.key} value={p.key}>
                {p.key} · {p.label}
              </option>
            ))}
          </select>
          <div className="spacer" style={{ flex: 1 }} />
          <button
            className="btn ghost"
            onClick={() => {
              onPatch(t.id, { archived: !t.archived })
              onClose()
            }}
          >
            {t.archived ? (
              '복원'
            ) : (
              <>
                <Svg name="archive" />
                아카이브
              </>
            )}
          </button>
          <button className="btn icon ghost" onClick={onClose}>
            <Svg name="close" />
          </button>
        </div>

        <div className="modal-body">
          <div className="field">
            <input
              className="title-input"
              type="text"
              value={t.summary}
              autoFocus={!t.summary}
              placeholder="태스크 제목…"
              onChange={(e) => onPatch(t.id, { summary: e.target.value })}
            />
          </div>

          <div className="field">
            <label>상태</label>
            <div className="choices">
              {STATUSES.map((s) => (
                <button
                  key={s.key}
                  className={'choice' + (t.status === s.key ? ' sel' : '')}
                  onClick={() => {
                    if (t.status !== s.key)
                      onPatch(t.id, { status: s.key }, { type: 'status', from: t.status, to: s.key })
                  }}
                >
                  <Lozenge status={s.key} />
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>담당자</label>
            <div className="choices">
              {[null, ...members].map((m) => {
                const sel = (t.assignee || null) === (m ? m.id : null)
                return (
                  <button
                    key={m ? m.id : 'none'}
                    className={'choice' + (sel ? ' sel' : '')}
                    onClick={() => {
                      const to = m ? m.id : null
                      if (t.assignee !== to)
                        onPatch(t.id, { assignee: to }, { type: 'assignee', from: t.assignee, to })
                    }}
                  >
                    <Avatar who={m} size="sm" />
                    <span style={{ fontSize: 11 }}>{m ? m.name : '미할당'}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="field-row" style={{ display: 'flex', gap: 12 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>우선순위</label>
              <div className="choices">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.key}
                    className={'choice' + (t.priority === p.key ? ' sel' : '')}
                    onClick={() => {
                      if (t.priority !== p.key)
                        onPatch(t.id, { priority: p.key }, { type: 'priority', from: t.priority, to: p.key })
                    }}
                  >
                    <PriIcon p={p.key} />
                    <span style={{ fontSize: 11 }}>{p.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>마감일</label>
              <input
                type="date"
                value={t.due || ''}
                onChange={(e) => {
                  const to = e.target.value || null
                  if ((t.due || null) !== to) onPatch(t.id, { due: to }, { type: 'due', from: t.due, to })
                }}
              />
            </div>
          </div>

          <div className="field">
            <label>메모</label>
            <textarea
              value={t.memo}
              placeholder="구현 메모, 재현 절차, 링크…"
              onChange={(e) => onPatch(t.id, { memo: e.target.value })}
            />
          </div>

          <div className="activity">
            <div className="activity-head">
              <label>활동</label>
              <div className="spacer" style={{ flex: 1 }} />
              <div className="tabs">
                {(
                  [
                    ['all', '전체', acts.length],
                    ['comment', '코멘트', comments.length],
                    ['event', '변경 이력', acts.length - comments.length],
                  ] as const
                ).map(([k, lbl, n]) => (
                  <button key={k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>
                    {lbl}
                    <span className="cnt">{n}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="stream">
              {shown.length === 0 && <div className="col-empty">아직 활동이 없습니다.</div>}
              {shown.map((a, i) => (
                <ActivityItem key={i} a={a} members={members} />
              ))}
            </div>

            <div className="comment-box">
              <Avatar who={meMember} size="md" />
              <div className="grow">
                <textarea
                  value={comment}
                  placeholder="코멘트 추가…  (⌘/Ctrl + Enter)"
                  onChange={(e) => setComment(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                      e.preventDefault()
                      submit()
                    }
                  }}
                />
                <div className="cb-foot">
                  <span className="hint">{meMember.name} (으)로 작성</span>
                  <button className="btn primary" onClick={submit}>
                    코멘트
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const EV_ICON: Record<string, string> = {
  created: 'ev_new',
  status: 'ev_status',
  assignee: 'ev_person',
  priority: 'ev_flag',
  due: 'ev_cal',
  edit: 'ev_edit',
}
const stLabel = (k: string | null | undefined) => STATUSES.find((s) => s.key === k)?.label || k || ''

function ActivityItem({ a, members }: { a: Activity; members: Member[] }) {
  const nameOf = (id: string | null | undefined) =>
    id ? members.find((m) => m.id === id)?.name || id : '미할당'

  if (a.type === 'comment') {
    return (
      <div className="act-item" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <Avatar who={a.who} size="sm" />
        <div className="bubble" style={{ flex: 1, minWidth: 0 }}>
          <div className="fi-line" style={{ fontSize: 12 }}>
            <b>{a.who?.name}</b>{' '}
            <span className="fi-time" style={{ color: 'var(--text-muted)' }}>
              · {relTime(a.ts)}
            </span>
          </div>
          <div className="fi-body" style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
            {a.text}
          </div>
        </div>
      </div>
    )
  }

  const text = (() => {
    switch (a.type) {
      case 'created':
        return '카드 생성'
      case 'status':
        return `${stLabel(a.from)} → ${stLabel(a.to)}`
      case 'assignee':
        return `담당자 ${nameOf(a.from)} → ${nameOf(a.to)}`
      case 'priority':
        return `우선순위 ${PRI_LABEL[a.from || ''] || '없음'} → ${PRI_LABEL[a.to || ''] || '없음'}`
      case 'due':
        return `마감일 ${a.from || '없음'} → ${a.to || '없음'}`
      case 'edit':
        return `${a.field || '필드'} 수정`
      default:
        return a.type
    }
  })()

  return (
    <div
      className="ev-chip"
      style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12, color: 'var(--text-subtle)' }}
    >
      <span className="ev-icon" style={{ opacity: 0.7 }}>
        <Svg name={EV_ICON[a.type] || 'ev_edit'} />
      </span>
      <span>{text}</span>
      <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
        {a.who?.name} · {relTime(a.ts)}
      </span>
    </div>
  )
}
