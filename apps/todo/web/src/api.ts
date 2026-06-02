import type { BoardData, Card } from './types'

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
