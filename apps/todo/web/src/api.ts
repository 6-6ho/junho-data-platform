import type { BoardData, Card } from './types'

export async function fetchBoard(): Promise<BoardData> {
  const r = await fetch('/api/board')
  if (!r.ok) throw new Error(`board load failed: ${r.status}`)
  return r.json()
}

export async function saveBoard(tasks: Card[], by?: string | null): Promise<void> {
  const r = await fetch('/api/board', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tasks, by }),
  })
  if (!r.ok) throw new Error(`board save failed: ${r.status}`)
}
