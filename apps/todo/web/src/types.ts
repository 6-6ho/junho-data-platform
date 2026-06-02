export type Status = 'todo' | 'doing' | 'done'
export type Priority = 'high' | 'med' | 'low'

export interface Member {
  id: string
  name: string
  initial: string
  tone: string
}

export interface Project {
  key: string
  label: string
}

export interface ActivityWho {
  name: string
  initial: string
  tone: string
}

export type ActivityType =
  | 'created'
  | 'comment'
  | 'status'
  | 'assignee'
  | 'priority'
  | 'due'
  | 'edit'

export interface Activity {
  type: ActivityType
  who: ActivityWho
  ts: string
  text?: string
  from?: string | null
  to?: string | null
  field?: string
}

export interface Card {
  id: string
  project: string
  num: number
  summary: string
  status: Status
  priority: Priority | null
  assignee: string | null
  due: string | null
  memo: string
  archived: boolean
  activity: Activity[]
}

export interface BoardData {
  tasks: Card[]
  members: Member[]
  projects: Project[]
}
