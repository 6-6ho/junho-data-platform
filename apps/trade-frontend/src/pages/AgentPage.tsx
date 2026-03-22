import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchAgentStats,
  fetchAgentCriteria,
  fetchAgentRecentMemos,
  addAgentMemo,
  searchAgentMemos,
  screenCoins,
  login,
  verifyAuth,
} from '../api/client';

function timeAgo(dateStr: string): string {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (diff < 60) return '방금';
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

const CATEGORY_LABELS: Record<string, string> = {
  entry: '진입', exit: '청산', risk: '리스크', general: '일반',
};

const CATEGORY_COLORS: Record<string, string> = {
  entry: '#10b981', exit: '#ef4444', risk: '#f59e0b', general: '#6b7280',
};

function AgentPage() {
  const queryClient = useQueryClient();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [password, setPassword] = useState('');
  const [memoInput, setMemoInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [screenResults, setScreenResults] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'memos' | 'screen'>('memos');

  // Auth check
  useQuery({
    queryKey: ['agent-auth'],
    queryFn: async () => {
      try {
        const token = localStorage.getItem('settings_token');
        if (!token) { setAuthed(false); return null; }
        await verifyAuth();
        setAuthed(true);
        return true;
      } catch {
        setAuthed(false);
        return null;
      }
    },
    retry: false,
  });

  // Public data
  const { data: stats } = useQuery({
    queryKey: ['agent-stats'],
    queryFn: fetchAgentStats,
    refetchInterval: 30_000,
  });
  const { data: criteriaData } = useQuery({
    queryKey: ['agent-criteria'],
    queryFn: fetchAgentCriteria,
    refetchInterval: 60_000,
  });
  const { data: memosData } = useQuery({
    queryKey: ['agent-recent-memos'],
    queryFn: () => fetchAgentRecentMemos(15),
    refetchInterval: 30_000,
  });

  const criteria = criteriaData?.criteria ?? [];
  const memos = memosData?.memos ?? [];

  // Mutations
  const loginMut = useMutation({
    mutationFn: () => login(password),
    onSuccess: (data: any) => {
      localStorage.setItem('settings_token', data.access_token);
      setAuthed(true);
      setPassword('');
    },
  });

  const addMemoMut = useMutation({
    mutationFn: () => addAgentMemo(memoInput),
    onSuccess: () => {
      setMemoInput('');
      queryClient.invalidateQueries({ queryKey: ['agent-recent-memos'] });
      queryClient.invalidateQueries({ queryKey: ['agent-stats'] });
    },
  });

  const searchMut = useMutation({
    mutationFn: () => searchAgentMemos(searchQuery),
    onSuccess: (data: any) => setSearchResults(data.results),
  });

  const screenMut = useMutation({
    mutationFn: screenCoins,
    onSuccess: (data: any) => setScreenResults(data),
  });

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* Stats */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', fontWeight: 'var(--font-semibold)' }}>
            Investment Agent
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-8)' }}>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.memo_count ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>메모</div>
            </div>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.criteria_count ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>투자 기준</div>
            </div>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.queries_today ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>오늘 질의</div>
            </div>
            {stats?.last_memo && (
              <div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)' }}>
                  {timeAgo(stats.last_memo)}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>마지막 메모</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Criteria */}
      {criteria.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ padding: 'var(--space-6)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
              투자 기준
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {criteria.map((c: any) => (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)',
                    fontWeight: 'var(--font-semibold)', color: '#fff',
                    background: CATEGORY_COLORS[c.category] || '#6b7280',
                  }}>
                    {CATEGORY_LABELS[c.category] || c.category}
                  </span>
                  <span style={{ fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)' }}>{c.name}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', flex: 1 }}>{c.content}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Auth Gate */}
      {authed === false && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
            <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
              메모 추가/검색/스크리닝은 로그인이 필요합니다
            </div>
            <form onSubmit={(e) => { e.preventDefault(); loginMut.mutate(); }} style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'center' }}>
              <input
                type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호"
                style={{ padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', width: 200 }}
              />
              <button type="submit" style={{ padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', cursor: 'pointer', fontWeight: 'var(--font-semibold)' }}>
                로그인
              </button>
            </form>
            {loginMut.isError && <div style={{ color: 'var(--red)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}>비밀번호가 틀렸습니다</div>}
          </div>
        </div>
      )}

      {/* Authenticated Section */}
      {authed && (
        <>
          {/* Tab Toggle */}
          <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            {(['memos', 'screen'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)', cursor: 'pointer',
                  fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)',
                  background: activeTab === tab ? 'var(--text-primary)' : 'var(--bg-secondary)',
                  color: activeTab === tab ? 'var(--bg-primary)' : 'var(--text-secondary)',
                }}
              >
                {tab === 'memos' ? '메모' : '스크리닝'}
              </button>
            ))}
          </div>

          {activeTab === 'memos' && (
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div className="card-body" style={{ padding: 'var(--space-6)' }}>
                {/* Add Memo */}
                <form onSubmit={(e) => { e.preventDefault(); if (memoInput.trim()) addMemoMut.mutate(); }} style={{ marginBottom: 'var(--space-4)' }}>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)', fontWeight: 'var(--font-semibold)' }}>메모 추가</div>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <input
                      value={memoInput} onChange={(e) => setMemoInput(e.target.value)}
                      placeholder="투자 인사이트를 입력하세요..."
                      style={{ flex: 1, padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                    />
                    <button type="submit" disabled={addMemoMut.isPending} style={{ padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'var(--font-semibold)' }}>
                      {addMemoMut.isPending ? '...' : '+'}
                    </button>
                  </div>
                </form>

                {/* Search */}
                <form onSubmit={(e) => { e.preventDefault(); if (searchQuery.trim()) searchMut.mutate(); }} style={{ marginBottom: 'var(--space-4)' }}>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)', fontWeight: 'var(--font-semibold)' }}>메모 검색</div>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <input
                      value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="검색어..."
                      style={{ flex: 1, padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                    />
                    <button type="submit" disabled={searchMut.isPending} style={{ padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', cursor: 'pointer', fontWeight: 'var(--font-semibold)' }}>
                      {searchMut.isPending ? '...' : '검색'}
                    </button>
                  </div>
                </form>

                {/* Search Results */}
                {searchResults && (
                  <div style={{ marginBottom: 'var(--space-4)' }}>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>검색 결과 ({searchResults.length}건)</div>
                    {searchResults.length === 0 ? (
                      <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', padding: 'var(--space-4)', textAlign: 'center' }}>결과 없음</div>
                    ) : (
                      searchResults.map((r: any) => (
                        <div key={r.id} style={{ padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', marginBottom: 'var(--space-1)', fontSize: 'var(--text-sm)' }}>
                          <div style={{ color: 'var(--text-primary)' }}>{r.content}</div>
                          <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
                            {r.tags?.join(', ')} {r.created_at && `| ${timeAgo(r.created_at)}`}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'screen' && (
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div className="card-body" style={{ padding: 'var(--space-6)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 'var(--font-semibold)' }}>스크리닝</div>
                  <button onClick={() => screenMut.mutate()} disabled={screenMut.isPending} style={{ padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', cursor: 'pointer', fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)' }}>
                    {screenMut.isPending ? '분석 중...' : '스크리닝 실행'}
                  </button>
                </div>

                {screenResults && (
                  <>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-3)' }}>
                      {screenResults.total}개 종목 | {screenResults.moving}개 움직이는 중
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                      {screenResults.coins?.map((c: any) => (
                        <div key={`${c.exchange}-${c.symbol}`} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', background: c.is_moving ? 'rgba(16,185,129,0.1)' : 'var(--bg-secondary)' }}>
                          <span style={{ fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)', minWidth: 50 }}>{c.symbol}</span>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', minWidth: 40 }}>{c.exchange}</span>
                          {c.volume_24h_krw && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{(c.volume_24h_krw / 1e8).toFixed(0)}억</span>}
                          {c.is_moving && c.move && (
                            <span style={{ marginLeft: 'auto', fontSize: 'var(--text-xs)', color: '#10b981', fontWeight: 'var(--font-semibold)' }}>
                              {c.move.change != null ? `${c.move.change > 0 ? '+' : ''}${c.move.change.toFixed(1)}%` : ''}
                              {c.move.vol_ratio != null ? ` (vol x${c.move.vol_ratio.toFixed(1)})` : ''}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Recent Memos (public) */}
      <div className="card">
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
            최근 메모
          </div>
          {memos.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: 'var(--space-8) 0' }}>메모 없음</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {memos.map((m: any) => (
                <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)' }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', flexShrink: 0 }}>#{m.id}</span>
                  <span style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)', flex: 1 }}>{m.preview}</span>
                  {m.tags?.length > 0 && (
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', flexShrink: 0 }}>{m.tags.join(', ')}</span>
                  )}
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', flexShrink: 0 }}>
                    {m.created_at ? timeAgo(m.created_at) : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AgentPage;
