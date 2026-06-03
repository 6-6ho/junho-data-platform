import type { CSSProperties } from 'react'
import type { Card as TCard, Member } from '../types'
import { Avatar, Due, PriIcon, Svg, keyOf, commentCount, memberById, projectTone } from '../lib'

export function Card({
  t,
  members,
  onOpen,
}: {
  t: TCard
  members: Member[]
  onOpen: (id: string) => void
}) {
  const cc = commentCount(t)
  return (
    <div
      className={'card' + (t.status === 'done' ? ' is-done' : '')}
      data-id={t.id}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', t.id)
        e.dataTransfer.effectAllowed = 'move'
        ;(e.currentTarget as HTMLElement).classList.add('dragging')
      }}
      onDragEnd={(e) => {
        ;(e.currentTarget as HTMLElement).classList.remove('dragging')
        document
          .querySelectorAll('.col-body.drag-over')
          .forEach((b) => b.classList.remove('drag-over'))
      }}
      onClick={(e) => {
        if (!(e.currentTarget as HTMLElement).classList.contains('dragging')) onOpen(t.id)
      }}
    >
      <div className="card-summary">
        {t.summary || <span style={{ color: 'var(--text-muted)' }}>(제목 없음)</span>}
      </div>

      {t.project && (
        <div className="card-tags">
          <span className="epic-tag" style={{ '--tag': projectTone(t.project) } as unknown as CSSProperties}>
            {t.project}
          </span>
        </div>
      )}

      <div className="card-meta">
        <span className="card-type" title="작업">
          <Svg name="task" />
        </span>
        <span className="keychip">{keyOf(t)}</span>
        <span className="spacer" />
        {t.memo && (
          <span className="memo-dot" title="메모">
            <Svg name="memo" />
          </span>
        )}
        {cc > 0 && (
          <span className="memo-dot" title={`코멘트 ${cc}`}>
            <Svg name="comment" />
            <span className="mono" style={{ fontSize: 10, marginLeft: 2 }}>
              {cc}
            </span>
          </span>
        )}
        <Due due={t.due} muted={t.status === 'done'} />
        <PriIcon p={t.priority} />
        <Avatar who={memberById(members, t.assignee)} size="sm" />
      </div>
    </div>
  )
}
