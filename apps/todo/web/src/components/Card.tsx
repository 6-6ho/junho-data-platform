import type { Card as TCard, Member } from '../types'
import { Avatar, Due, PriIcon, Svg, keyOf, commentCount, memberById } from '../lib'

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
      <div className="card-top">
        <span className="keychip">{keyOf(t)}</span>
        <span className="spacer" />
        <PriIcon p={t.priority} />
      </div>
      <div className="card-summary">
        {t.summary || <span style={{ color: 'var(--text-muted)' }}>(제목 없음)</span>}
      </div>
      <div className="card-meta">
        <Avatar who={memberById(members, t.assignee)} size="sm" />
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
      </div>
    </div>
  )
}
