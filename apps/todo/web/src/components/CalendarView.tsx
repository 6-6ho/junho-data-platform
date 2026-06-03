import { useEffect, useRef, useState } from 'react'
import type { Card } from '../types'
import { fetchGoal, saveGoal } from '../api'
import { MonthCalendar } from './MonthCalendar'
import { monthKey, addMonths, monthLabelKo, keyOf } from '../lib'

export function CalendarView({
  tasks,
  onOpen,
  me,
}: {
  tasks: Card[]
  onOpen: (id: string) => void
  me: string | null
}) {
  const [month, setMonth] = useState(() => monthKey(new Date()))
  const [goal, setGoal] = useState('')
  const [goalLoaded, setGoalLoaded] = useState(false)
  const firstGoalSave = useRef(true)
  const focused = useRef(false)

  // 마감일 기준으로 날짜별 묶기
  const byDate: Record<string, Card[]> = {}
  for (const t of tasks) if (t.due) (byDate[t.due] ||= []).push(t)

  // 월 바뀌면 목표 로드
  useEffect(() => {
    let alive = true
    setGoalLoaded(false)
    firstGoalSave.current = true
    fetchGoal(month)
      .then((txt) => alive && (setGoal(txt), setGoalLoaded(true)))
      .catch(() => alive && setGoalLoaded(true))
    return () => {
      alive = false
    }
  }, [month])

  // 목표 디바운스 저장
  useEffect(() => {
    if (!goalLoaded) return
    if (firstGoalSave.current) {
      firstGoalSave.current = false
      return
    }
    const id = setTimeout(() => saveGoal(month, goal, me).catch(() => {}), 700)
    return () => clearTimeout(id)
  }, [goal, goalLoaded, month, me])

  // 10초 폴링 — 입력 중이 아니면 다른 사람 변경 반영
  useEffect(() => {
    const id = setInterval(async () => {
      if (focused.current) return
      try {
        const txt = await fetchGoal(month)
        setGoal((cur) => (cur === txt ? cur : txt))
      } catch {
        /* 무시 */
      }
    }, 10000)
    return () => clearInterval(id)
  }, [month])

  return (
    <div className="calendar">
      <div className="cal-main">
        <div className="cal-nav">
          <button className="cal-arrow" onClick={() => setMonth(addMonths(month, -1))} title="이전 달">
            ‹
          </button>
          <h2 className="cal-month">{monthLabelKo(month)}</h2>
          <button className="cal-arrow" onClick={() => setMonth(addMonths(month, 1))} title="다음 달">
            ›
          </button>
          <button className="cal-today" onClick={() => setMonth(monthKey(new Date()))}>
            오늘
          </button>
        </div>

        <MonthCalendar
          month={month}
          renderCell={(iso) => {
            const items = byDate[iso] || []
            if (!items.length) return null
            const shown = items.slice(0, 3)
            return (
              <div className="cal-chips">
                {shown.map((t) => (
                  <button
                    key={t.id}
                    className={`cal-chip st-${t.status}`}
                    title={`${keyOf(t)} · ${t.summary || '(제목 없음)'}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      onOpen(t.id)
                    }}
                  >
                    {t.summary || keyOf(t)}
                  </button>
                ))}
                {items.length > 3 && <div className="cal-more">+{items.length - 3}</div>}
              </div>
            )
          }}
        />
      </div>

      <aside className="cal-goals">
        <h3>{monthLabelKo(month)} 목표</h3>
        <textarea
          value={goal}
          disabled={!goalLoaded}
          placeholder={'이번 달 목표를 자유롭게 적어요…\n- 로또 v2 배포\n- 사주 결제 모듈\n이번달은 출시에 집중!'}
          onFocus={() => (focused.current = true)}
          onBlur={() => (focused.current = false)}
          onChange={(e) => setGoal(e.target.value)}
        />
        <div className="cal-goals-hint">자동 저장 · 팀 공유</div>
      </aside>
    </div>
  )
}
