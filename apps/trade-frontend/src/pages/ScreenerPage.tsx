import { useState, useEffect, useCallback, useMemo } from 'react';
import { AlertTriangle, TrendingDown, Zap, BarChart3, ChevronUp, ChevronDown, Search } from 'lucide-react';

const API_BASE = '/api/screener';

interface ScreenerOverview {
  total: number;
  junk_count: number;
  low_cap_count: number;
  long_decline_count: number;
  no_pump_count: number;
  last_updated: string | null;
}

interface ScreenerCoin {
  exchange: string;
  symbol: string;
  price_krw: number | null;
  market_cap_krw: number | null;
  volume_24h_krw: number | null;
  weekly_down_count: number | null;
  listing_age_days: number | null;
  is_low_cap: boolean;
  is_long_decline: boolean;
  is_no_pump: boolean;
  junk_score: number;
  updated_at: string | null;
}

type FilterFlag = '' | 'junk' | 'low_cap' | 'long_decline' | 'no_pump';
type FilterExchange = '' | 'upbit' | 'bithumb';
type SortKey = 'symbol' | 'exchange' | 'price_krw' | 'market_cap_krw' | 'volume_24h_krw' | 'weekly_down_count' | 'junk_score';
type SortDir = 'asc' | 'desc';

const formatKRW = (v: number | null) => {
  if (v == null) return '—';
  if (v >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(1)}조`;
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(0)}억`;
  if (v >= 10_000) return `${(v / 10_000).toFixed(0)}만`;
  return v.toLocaleString();
};

const formatPrice = (v: number | null) => {
  if (v == null) return '—';
  if (v >= 1_000_000) return `${(v / 10_000).toFixed(0)}만`;
  return v.toLocaleString('ko-KR', { maximumFractionDigits: 2 });
};

const scoreColor = (score: number): string => {
  if (score >= 3) return '#ff5252';
  if (score === 2) return '#ff9800';
  if (score === 1) return '#ffd740';
  return 'var(--text-tertiary)';
};

const scoreBg = (score: number): string => {
  if (score >= 3) return 'rgba(255,82,82,0.12)';
  if (score === 2) return 'rgba(255,152,0,0.10)';
  if (score === 1) return 'rgba(255,215,64,0.08)';
  return 'transparent';
};

function compareValues(a: unknown, b: unknown, dir: SortDir): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === 'string' && typeof b === 'string') {
    return dir === 'asc' ? a.localeCompare(b) : b.localeCompare(a);
  }
  const na = Number(a), nb = Number(b);
  return dir === 'asc' ? na - nb : nb - na;
}

const selectStyle: React.CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 6,
  color: 'var(--text-primary)',
  fontSize: 'var(--text-sm)',
  padding: '6px 12px',
  outline: 'none',
  cursor: 'pointer',
};

export default function ScreenerPage() {
  const [overview, setOverview] = useState<ScreenerOverview | null>(null);
  const [coins, setCoins] = useState<ScreenerCoin[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterExchange, setFilterExchange] = useState<FilterExchange>('');
  const [filterFlag, setFilterFlag] = useState<FilterFlag>('');
  const [filterScore, setFilterScore] = useState<'' | '0' | '1' | '2' | '3'>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('junk_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const fetchOverview = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/overview`);
      const data = await res.json();
      setOverview(data);
    } catch (e) {
      console.error('Failed to fetch screener overview:', e);
    }
  }, []);

  const fetchCoins = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterExchange) params.set('exchange', filterExchange);
      if (filterFlag) params.set('flag', filterFlag);
      const qs = params.toString();
      const res = await fetch(`${API_BASE}/coins${qs ? `?${qs}` : ''}`);
      const data = await res.json();
      setCoins(data.coins || []);
    } catch (e) {
      console.error('Failed to fetch screener coins:', e);
    } finally {
      setLoading(false);
    }
  }, [filterExchange, filterFlag]);

  useEffect(() => { fetchOverview(); }, [fetchOverview]);
  useEffect(() => { setLoading(true); fetchCoins(); }, [fetchCoins]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'symbol' || key === 'exchange' ? 'asc' : 'desc');
    }
  };

  const sortedCoins = useMemo(() => {
    let filtered = coins;
    if (searchQuery) {
      const q = searchQuery.toUpperCase();
      filtered = filtered.filter(c => c.symbol.includes(q));
    }
    if (filterScore !== '') {
      const score = Number(filterScore);
      filtered = filtered.filter(c => c.junk_score === score);
    }
    return [...filtered].sort((a, b) => compareValues(a[sortKey], b[sortKey], sortDir));
  }, [coins, searchQuery, filterScore, sortKey, sortDir]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--space-3)' }}>
        <SummaryCard label="전체 종목" value={overview?.total ?? 0} icon={<BarChart3 size={16} />} color="var(--text-secondary)" />
        <SummaryCard label="잡코인" value={overview?.junk_count ?? 0} icon={<AlertTriangle size={16} />} color="#ff5252" />
        <SummaryCard label="저시총" value={overview?.low_cap_count ?? 0} icon={<Zap size={16} />} color="#ff9800" />
        <SummaryCard label="장기하락" value={overview?.long_decline_count ?? 0} icon={<TrendingDown size={16} />} color="#ffd740" />
        <SummaryCard label="무펌핑" value={overview?.no_pump_count ?? 0} icon={<TrendingDown size={16} />} color="#90a4ae" />
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-body" style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
          <select
            value={filterExchange}
            onChange={e => setFilterExchange(e.target.value as FilterExchange)}
            style={selectStyle}
          >
            <option value="">거래소: 전체</option>
            <option value="upbit">업비트</option>
            <option value="bithumb">빗썸</option>
          </select>

          <select
            value={filterFlag}
            onChange={e => setFilterFlag(e.target.value as FilterFlag)}
            style={selectStyle}
          >
            <option value="">분류: 전체</option>
            <option value="junk">잡코인 (score&gt;0)</option>
            <option value="low_cap">저시총</option>
            <option value="long_decline">장기하락</option>
            <option value="no_pump">무펌핑</option>
          </select>

          <select
            value={filterScore}
            onChange={e => setFilterScore(e.target.value as '' | '0' | '1' | '2' | '3')}
            style={selectStyle}
          >
            <option value="">Score: 전체</option>
            <option value="3">3</option>
            <option value="2">2</option>
            <option value="1">1</option>
            <option value="0">0</option>
          </select>

          <div style={{ flex: 1 }} />

          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} style={{ position: 'absolute', left: 8, color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              placeholder="심볼 검색"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 12px 6px 28px',
                borderRadius: 6,
                border: '1px solid #333',
                fontSize: 'var(--text-sm)',
                backgroundColor: '#1a1a1a',
                color: 'var(--text-primary)',
                width: 140,
                outline: 'none',
              }}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        <div className="card-body" style={{ padding: 0, overflowX: 'auto' }}>
          {loading ? (
            <div style={{ padding: 'var(--space-10)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              로딩 중...
            </div>
          ) : sortedCoins.length === 0 ? (
            <div style={{ padding: 'var(--space-10)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              {searchQuery ? `"${searchQuery}" 검색 결과 없음` : '데이터 없음 — DAG 실행 후 확인하세요'}
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <SortTh sortKey="symbol" currentKey={sortKey} dir={sortDir} onSort={handleSort}>종목</SortTh>
                  <SortTh sortKey="exchange" currentKey={sortKey} dir={sortDir} onSort={handleSort}>거래소</SortTh>
                  <SortTh sortKey="price_krw" currentKey={sortKey} dir={sortDir} onSort={handleSort} align="right">현재가</SortTh>
                  <SortTh sortKey="market_cap_krw" currentKey={sortKey} dir={sortDir} onSort={handleSort} align="right">시총</SortTh>
                  <SortTh sortKey="volume_24h_krw" currentKey={sortKey} dir={sortDir} onSort={handleSort} align="right">거래대금</SortTh>
                  <SortTh sortKey="weekly_down_count" currentKey={sortKey} dir={sortDir} onSort={handleSort} align="center">음봉(12주)</SortTh>
                  <SortTh sortKey="junk_score" currentKey={sortKey} dir={sortDir} onSort={handleSort} align="center">Score</SortTh>
                  <Th>분류</Th>
                </tr>
              </thead>
              <tbody>
                {sortedCoins.map((coin) => (
                  <tr
                    key={`${coin.exchange}-${coin.symbol}`}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: scoreBg(coin.junk_score),
                    }}
                  >
                    <Td>
                      <span style={{ fontWeight: 600 }}>{coin.symbol}</span>
                    </Td>
                    <Td>
                      <span style={{
                        fontSize: 'var(--text-xs)',
                        padding: '1px 6px',
                        borderRadius: 4,
                        backgroundColor: coin.exchange === 'upbit' ? 'rgba(0,100,255,0.1)' : 'rgba(255,165,0,0.1)',
                        color: coin.exchange === 'upbit' ? '#4a90d9' : '#e8a838',
                      }}>
                        {coin.exchange === 'upbit' ? '업비트' : '빗썸'}
                      </span>
                    </Td>
                    <Td align="right">{formatPrice(coin.price_krw)}원</Td>
                    <Td align="right">{formatKRW(coin.market_cap_krw)}</Td>
                    <Td align="right">{formatKRW(coin.volume_24h_krw)}</Td>
                    <Td align="center">
                      {coin.weekly_down_count != null ? (
                        <span style={{ color: coin.weekly_down_count >= 8 ? '#ff5252' : 'var(--text-secondary)' }}>
                          {coin.weekly_down_count}/12
                        </span>
                      ) : '—'}
                    </Td>
                    <Td align="center">
                      <span style={{
                        fontWeight: 700,
                        fontSize: 'var(--text-base)',
                        color: scoreColor(coin.junk_score),
                      }}>
                        {coin.junk_score}
                      </span>
                    </Td>
                    <Td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {coin.is_low_cap && <Tag color="#ff9800">저시총</Tag>}
                        {coin.is_long_decline && <Tag color="#ffd740">장기하락</Tag>}
                        {coin.is_no_pump && <Tag color="#90a4ae">무펌핑</Tag>}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div style={{
          padding: 'var(--space-2) var(--space-4)',
          fontSize: 'var(--text-xs)',
          color: 'var(--text-tertiary)',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span>{sortedCoins.length}개 종목</span>
          {overview?.last_updated && (
            <span>마지막 업데이트: {new Date(overview.last_updated).toLocaleString('ko-KR')}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, icon, color }: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="card">
      <div className="card-body" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color }}>
          {icon}
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>{label}</span>
        </div>
        <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color }}>
          {value}
        </div>
      </div>
    </div>
  );
}

function Tag({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span style={{
      fontSize: 'var(--text-xs)',
      padding: '1px 6px',
      borderRadius: 4,
      backgroundColor: `${color}20`,
      color,
      fontWeight: 500,
      whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  );
}

function SortTh({ children, sortKey, currentKey, dir, onSort, align = 'left' }: {
  children: React.ReactNode;
  sortKey: SortKey;
  currentKey: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
  align?: string;
}) {
  const isActive = sortKey === currentKey;
  return (
    <th
      onClick={() => onSort(sortKey)}
      style={{
        padding: 'var(--space-3) var(--space-4)',
        textAlign: align as 'left' | 'right' | 'center',
        fontWeight: 600,
        fontSize: 'var(--text-xs)',
        color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        cursor: 'pointer',
        userSelect: 'none',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
      {isActive ? (
        dir === 'asc'
          ? <ChevronUp size={12} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
          : <ChevronDown size={12} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
      ) : null}
    </th>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th style={{
      padding: 'var(--space-3) var(--space-4)',
      textAlign: 'left',
      fontWeight: 600,
      fontSize: 'var(--text-xs)',
      color: 'var(--text-tertiary)',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {children}
    </th>
  );
}

function Td({ children, align = 'left' }: { children: React.ReactNode; align?: string }) {
  return (
    <td style={{
      padding: 'var(--space-2) var(--space-4)',
      textAlign: align as 'left' | 'right' | 'center',
      whiteSpace: 'nowrap',
    }}>
      {children}
    </td>
  );
}
