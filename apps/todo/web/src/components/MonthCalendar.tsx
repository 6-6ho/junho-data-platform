import type { ReactNode } from 'react'
import { monthGrid, monthKey, WEEKDAYS_KO, todayISO } from '../lib'

export function MonthCalendar({
  month,
  selected,
  onPick,
  renderCell,
  compact,
}: {
  month: string // 'YYYY-MM'
  selected?: string | null
  onPick?: (iso: string) => void
  renderCell?: (iso: string) => ReactNode
  compact?: boolean
}) {
  const days = monthGrid(month)
  const today = todayISO()
  return (
    <div className={'mcal' + (compact ? ' compact' : '')}>
      <div className="mcal-wd">
        {WEEKDAYS_KO.map((w, i) => (
          <div key={w} className={'mcal-wd-cell' + (i === 0 ? ' sun' : i === 6 ? ' sat' : '')}>
            {w}
          </div>
        ))}
      </div>
      <div className="mcal-grid">
        {days.map((iso) => {
          const d = new Date(iso + 'T00:00:00')
          const inMonth = monthKey(d) === month
          const dow = d.getDay()
          const cls = ['mcal-cell']
          if (!inMonth) cls.push('out')
          if (iso === today) cls.push('today')
          if (selected && iso === selected) cls.push('sel')
          if (dow === 0) cls.push('sun')
          if (dow === 6) cls.push('sat')
          return (
            <div
              key={iso}
              className={cls.join(' ')}
              onClick={onPick ? () => onPick(iso) : undefined}
              role={onPick ? 'button' : undefined}
            >
              <div className="mcal-daynum">{d.getDate()}</div>
              {renderCell && <div className="mcal-cell-body">{renderCell(iso)}</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
