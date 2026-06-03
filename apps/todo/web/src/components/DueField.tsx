import { useState } from 'react'
import { Svg, fmtDateKo, todayISO, addDays, addMonths, monthKey, monthLabelKo } from '../lib'
import { MonthCalendar } from './MonthCalendar'

function nextDow(from: string, dow: number): string {
  let i = 1
  while (new Date(addDays(from, i) + 'T00:00:00').getDay() !== dow) i++
  return addDays(from, i)
}

export function DueField({
  value,
  onChange,
}: {
  value: string | null
  onChange: (iso: string | null) => void
}) {
  const [open, setOpen] = useState(false)
  const [popMonth, setPopMonth] = useState(() =>
    monthKey(new Date((value || todayISO()) + 'T00:00:00')),
  )

  const today = todayISO()
  const quicks: [string, string][] = [
    ['오늘', today],
    ['내일', addDays(today, 1)],
    ['이번 주말', nextDow(today, 6)],
    ['다음 주', nextDow(today, 1)],
  ]

  function openPop() {
    setPopMonth(monthKey(new Date((value || today) + 'T00:00:00')))
    setOpen((o) => !o)
  }

  return (
    <div className="due-field">
      <div className="due-quick">
        {quicks.map(([label, iso]) => (
          <button
            key={label}
            type="button"
            className={'due-chip' + (value === iso ? ' on' : '')}
            onClick={() => onChange(iso)}
          >
            {label}
          </button>
        ))}
        <button type="button" className="due-chip clear" onClick={() => onChange(null)}>
          지우기
        </button>
      </div>

      <button type="button" className="due-trigger" onClick={openPop}>
        <Svg name="cal" />
        <span className={value ? '' : 'muted'}>{value ? fmtDateKo(value) : '마감일 없음'}</span>
      </button>

      {open && (
        <>
          <div className="cal-pop-backdrop" onClick={() => setOpen(false)} />
          <div className="cal-pop">
            <div className="cal-pop-nav">
              <button type="button" onClick={() => setPopMonth(addMonths(popMonth, -1))}>
                ‹
              </button>
              <span>{monthLabelKo(popMonth)}</span>
              <button type="button" onClick={() => setPopMonth(addMonths(popMonth, 1))}>
                ›
              </button>
            </div>
            <MonthCalendar
              month={popMonth}
              selected={value}
              compact
              onPick={(iso) => {
                onChange(iso)
                setOpen(false)
              }}
            />
          </div>
        </>
      )}
    </div>
  )
}
