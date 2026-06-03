import { useState } from 'react'
import type { Project } from '../types'
import { Svg } from '../lib'

export function ProjectManager({
  projects,
  onSave,
  onClose,
}: {
  projects: Project[]
  onSave: (list: Project[]) => Promise<void>
  onClose: () => void
}) {
  const [list, setList] = useState<Project[]>(projects)
  const [key, setKey] = useState('')
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  function add() {
    const k = key.trim().toUpperCase()
    const l = label.trim() || k
    if (!k) return
    if (!/^[A-Z0-9]{1,12}$/.test(k)) {
      setErr('KEY 는 영문/숫자 1~12자 (예: MARKETING)')
      return
    }
    if (list.some((p) => p.key === k)) {
      setErr('이미 있는 KEY 예요')
      return
    }
    setErr(null)
    setList([...list, { key: k, label: l }])
    setKey('')
    setLabel('')
  }

  const remove = (k: string) => setList(list.filter((p) => p.key !== k))

  async function save() {
    if (!list.length) {
      setErr('프로젝트는 최소 1개 있어야 해요')
      return
    }
    setBusy(true)
    try {
      await onSave(list)
      onClose()
    } catch (e) {
      setErr(String(e))
      setBusy(false)
    }
  }

  return (
    <div
      className="overlay open"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '48px 16px',
        zIndex: 60,
        overflow: 'auto',
      }}
    >
      <div className="modal proj-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-kind">프로젝트 관리</span>
          <div className="spacer" style={{ flex: 1 }} />
          <button className="btn icon ghost" onClick={onClose} title="닫기">
            <Svg name="close" />
          </button>
        </div>

        <div className="modal-body">
          <div className="proj-list">
            {list.map((p) => (
              <div key={p.key} className="proj-row">
                <span className="proj-key">{p.key}</span>
                <span className="proj-label">{p.label}</span>
                <button className="proj-del" title="제거" onClick={() => remove(p.key)}>
                  <Svg name="close" />
                </button>
              </div>
            ))}
            {!list.length && <div className="col-empty">프로젝트가 없습니다. 아래에서 추가하세요.</div>}
          </div>

          <div className="field">
            <label>새 프로젝트 추가</label>
            <div className="proj-add">
              <input
                className="proj-key-in"
                placeholder="KEY (예: MARKETING)"
                value={key}
                maxLength={12}
                onChange={(e) => setKey(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && add()}
              />
              <input
                className="proj-label-in"
                placeholder="이름 (예: 마케팅)"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && add()}
              />
              <button className="btn" onClick={add}>
                추가
              </button>
            </div>
            {err && <div className="proj-err">{err}</div>}
          </div>

          <div className="proj-hint">
            KEY 는 카드 번호에 쓰여요 (예: <b>MARKETING-1</b>). 사용 중인 프로젝트를 제거해도 기존
            카드의 KEY 는 남습니다.
          </div>
        </div>

        <div className="modal-foot">
          <div className="spacer" style={{ flex: 1 }} />
          <button className="btn" onClick={onClose}>
            취소
          </button>
          <button className="btn primary" disabled={busy} onClick={save}>
            {busy ? '저장 중…' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
