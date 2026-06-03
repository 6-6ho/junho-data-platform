import type { BoardData, Card, Project } from './types'

export async function fetchBoard(): Promise<BoardData> {
  const r = await fetch('/api/board')
  if (!r.ok) throw new Error(`board load failed: ${r.status}`)
  return r.json()
}

export type SaveResult =
  | { ok: true; rev: number }
  | { ok: false; conflict: true; rev: number; tasks: Card[] }

/** base_rev 기반 낙관적 저장. 409(다른 사람이 먼저 저장) 면 최신 rev+tasks 를 돌려준다. */
export async function saveBoard(
  tasks: Card[],
  baseRev: number,
  by?: string | null,
): Promise<SaveResult> {
  const r = await fetch('/api/board', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tasks, base_rev: baseRev, by }),
  })
  if (r.status === 409) {
    const d = await r.json()
    return { ok: false, conflict: true, rev: d.rev, tasks: d.tasks }
  }
  if (!r.ok) throw new Error(`board save failed: ${r.status}`)
  const d = await r.json()
  return { ok: true, rev: d.rev }
}

// ---- 그 달의 목표 (월별 자유 메모) ----
export async function fetchGoal(month: string): Promise<string> {
  const r = await fetch(`/api/goals?month=${encodeURIComponent(month)}`)
  if (!r.ok) throw new Error(`goal load failed: ${r.status}`)
  const d = await r.json()
  return d.text || ''
}

export async function saveGoal(month: string, text: string, by?: string | null): Promise<void> {
  const r = await fetch('/api/goals', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ month, text, by }),
  })
  if (!r.ok) throw new Error(`goal save failed: ${r.status}`)
}

// ---- 프로젝트 목록 (사용자 관리, 전체 교체) ----
export async function saveProjects(projects: Project[], by?: string | null): Promise<Project[]> {
  const r = await fetch('/api/projects', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projects, by }),
  })
  if (!r.ok) throw new Error(`projects save failed: ${r.status}`)
  const d = await r.json()
  return d.projects as Project[]
}
