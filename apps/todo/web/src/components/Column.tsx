import { useState } from 'react'
import type { Card as TCard, Member, Status } from '../types'
import { COL_TONE, Svg } from '../lib'
import { Card } from './Card'

function getDragAfterId(container: HTMLElement, y: number): string | null {
  const cards = [...container.querySelectorAll('.card:not(.dragging)')] as HTMLElement[]
  let closest = { offset: -Infinity, id: null as string | null }
  for (const c of cards) {
    const box = c.getBoundingClientRect()
    const offset = y - box.top - box.height / 2
    if (offset < 0 && offset > closest.offset) closest = { offset, id: c.dataset.id || null }
  }
  return closest.id
}

export function Column({
  col,
  items,
  members,
  onCreate,
  onOpen,
  onMove,
}: {
  col: { key: Status; label: string }
  items: TCard[]
  members: Member[]
  onCreate: (status: Status) => void
  onOpen: (id: string) => void
  onMove: (id: string, status: Status, beforeId: string | null) => void
}) {
  const [over, setOver] = useState(false)
  return (
    <div className="column">
      <div className="col-head">
        <span className="col-accent" style={{ background: COL_TONE[col.key] }} />
        <span className="col-title">{col.label}</span>
        <span className="col-count">{items.length}</span>
      </div>
      <div
        className={'col-body' + (over ? ' drag-over' : '')}
        data-status={col.key}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false)
        }}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          const id = e.dataTransfer.getData('text/plain')
          const beforeId = getDragAfterId(e.currentTarget as HTMLElement, e.clientY)
          if (id) onMove(id, col.key, beforeId)
        }}
      >
        {items.length === 0 && <div className="col-empty">비어 있음</div>}
        {items.map((t) => (
          <Card key={t.id} t={t} members={members} onOpen={onOpen} />
        ))}
      </div>
      <div className="col-foot">
        <button className="col-add" onClick={() => onCreate(col.key)}>
          <Svg name="plus" />
          만들기
        </button>
      </div>
    </div>
  )
}
