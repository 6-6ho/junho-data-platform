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
import { DueField } from './DueField'

export function CardModal({
  t,
  mode,
  members,
  projects,
  me,
  onChange,
  onPrimary,
  onCancel,
  onDelete,
  onComment,
}: {
  t: Card
  mode: 'create' | 'edit'
  members: Member[]
  projects: Project[]
  me: string | null
  onChange: (patch: Partial<Card>, ev?: Partial<Activity>) => void
  onPrimary?: () => void
  onCancel: () => void
  onDelete?: () => void
  onComment?: (text: string) => void
}) {
  const isCreate = mode === 'create'
  const [tab, setTab] = useState<'all' | 'comment' | 'event'>('all')
  const [comment, setComment] = useState('')
  const [actOpen, setActOpen] = useState(() => localStorage.getItem('kanban.actOpen') !== '0')
  const toggleAct = () => {
    setActOpen((v) => {
      localStorage.setItem('kanban.actOpen', v ? '0' : '1')
      return !v
    })
  }
  const meMember = members.find((m) => m.id === me) || { name: '게스트', initial: '?', tone: 'tx' }

  const acts = [...(t.activity || [])].sort(
    (a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime(),
  )
  const comments = acts.filter((a) => a.type === 'comment')
  const shown = acts.filter((a) =>
    tab === 'all' ? true : tab === 'comment' ? a.type === 'comment' : a.type !== 'comment',
  )

  const canCreate = (t.summary || '').trim().length > 0

  function submit() {
    const v = comment.trim()
    if (!v || !onComment) return
    onComment(v)
    setComment('')
  }

  return (
    <div
      className="overlay open"
      onClick={onCancel}
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
          {isCreate ? (
            <span className="modal-kind">새 카드</span>
          ) : (
            <span className="keychip">{keyOf(t)}</span>
          )}
          <select
            className="filter-select"
            value={t.project}
            onChange={(e) => onChange({ project: e.target.value }, { type: 'edit', field: 'project' })}
          >
            {!projects.some((p) => p.key === t.project) && <option value={t.project}>{t.project}</option>}
            {projects.map((p) => (
              <option key={p.key} value={p.key}>
                {p.key} · {p.label}
              </option>
            ))}
          </select>
          <div className="spacer" style={{ flex: 1 }} />
          {!isCreate && (
            <button
              className="btn ghost"
              onClick={() => {
                onChange({ archived: !t.archived })
                onCancel()
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
          )}
          <button className="btn icon ghost" onClick={onCancel} title="닫기">
            <Svg name="close" />
          </button>
        </div>

        <div className="modal-body">
          <div className="field">
            <input
              className="title-input"
              type="text"
              value={t.summary}
              autoFocus={isCreate || !t.summary}
              placeholder="할 일 제목을 입력하세요…"
              onChange={(e) => onChange({ summary: e.target.value })}
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
                      onChange({ status: s.key }, { type: 'status', from: t.status, to: s.key })
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
                        onChange({ assignee: to }, { type: 'assignee', from: t.assignee, to })
                    }}
                  >
                    <Avatar who={m} size="sm" />
                    <span>{m ? m.name : '미할당'}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="field-row" style={{ display: 'flex', gap: 14 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>우선순위</label>
              <div className="choices">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.key}
                    className={'choice' + (t.priority === p.key ? ' sel' : '')}
                    onClick={() => {
                      if (t.priority !== p.key)
                        onChange({ priority: p.key }, { type: 'priority', from: t.priority, to: p.key })
                    }}
                  >
                    <PriIcon p={p.key} />
                    <span>{p.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>마감일</label>
              <DueField
                value={t.due}
                onChange={(to) => {
                  if ((t.due || null) !== to) onChange({ due: to }, { type: 'due', from: t.due, to })
                }}
              />
            </div>
          </div>

          <div className="field">
            <label>메모</label>
            <textarea
              value={t.memo}
              placeholder="구현 메모, 재현 절차, 링크…"
              onChange={(e) => onChange({ memo: e.target.value })}
            />
          </div>

          {!isCreate && (
            <div className={'activity' + (actOpen ? '' : ' collapsed')}>
              <div className="activity-head">
                <button type="button" className="act-toggle" onClick={toggleAct}>
                  <span className="act-caret">{actOpen ? '▾' : '▸'}</span>
                  활동
                  <span className="act-count">{acts.length}</span>
                </button>
                <div className="spacer" style={{ flex: 1 }} />
                {actOpen && (
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
                )}
              </div>

              {actOpen && (
                <>
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
                </>
              )}
            </div>
          )}
        </div>

        <div className="modal-foot">
          {!isCreate && onDelete && (
            <button className="btn danger" onClick={onDelete}>
              <Svg name="trash" />
              삭제
            </button>
          )}
          <div className="spacer" style={{ flex: 1 }} />
          <button className="btn" onClick={onCancel}>
            {isCreate ? '취소' : '닫기'}
          </button>
          {isCreate && (
            <button className="btn primary" disabled={!canCreate} onClick={onPrimary}>
              생성
            </button>
          )}
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
          <div className="fi-line" style={{ fontSize: 13 }}>
            <b>{a.who?.name}</b>{' '}
            <span className="fi-time" style={{ color: 'var(--text-muted)' }}>
              · {relTime(a.ts)}
            </span>
          </div>
          <div className="fi-body" style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>
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
      style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, color: 'var(--text-subtle)' }}
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
