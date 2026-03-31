import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { TrendingUp, Users, Link2, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import {
  fetchWeeklySummary, fetchMartWeeklyTrend, fetchCategoryRanking,
  fetchMartRFM, fetchMartAssociation,
} from '../api/client';

const CL = ['#22C55E', '#3B82F6', '#A855F7', '#F59E0B', '#EF4444'];
const TIP = {
  contentStyle: { backgroundColor: '#0F0F0F', border: '1px solid #303030', borderRadius: 4, fontSize: 11, fontFamily: "'IBM Plex Mono',monospace", padding: '6px 10px' },
  itemStyle: { color: '#E2E2E2', fontSize: 11, fontFamily: "'IBM Plex Mono',monospace" },
};
const AX = { fill: '#4A4A4A', fontSize: 10, fontFamily: "'IBM Plex Mono',monospace" };

const krw = (n: number | null | undefined) => { if (n == null) return '--'; if (n >= 1e12) return `${(n / 1e12).toFixed(1)}조`; if (n >= 1e8) return `${(n / 1e8).toFixed(1)}억`; if (n >= 1e4) return `${(n / 1e4).toFixed(0)}만`; return `₩${n.toLocaleString()}`; };
const fN = (n: number | null | undefined) => { if (n == null) return '--'; if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`; if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`; if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`; return n.toLocaleString(); };
const fD = (d: string) => { try { return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }); } catch { return d; } };

function Trend({ value }: { value: number | null | undefined }) {
  if (value == null) return null;
  const up = value >= 0;
  return (
    <span className={`trend ${up ? 'trend-up' : 'trend-down'}`}>
      {up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

function Sk({ h = 220 }: { h?: number }) { return <div className="sk" style={{ width: '100%', height: h }} />; }

interface WeeklySummary { week_start: string; revenue: number; orders: number; wow_revenue_pct: number | null; wow_orders_pct: number | null; best_category: string | null; best_category_revenue: number | null; total_week_revenue: number }
interface CatRank { category: string; revenue: number; orders: number; wow_pct: number | null; share_pct: number }
interface RFM { segment: string; user_count: number }
interface Assoc { antecedents: string; consequents: string; confidence: number; lift: number; support: number }
interface Weekly { week: string; revenue: number; orders: number }

export default function MartPage() {
  const { data: ws, isLoading: wsL } = useQuery<WeeklySummary>({ queryKey: ['weekly-summary'], queryFn: fetchWeeklySummary, staleTime: 300_000 });
  const { data: weekly = [], isLoading: wL } = useQuery<Weekly[]>({ queryKey: ['weekly-trend'], queryFn: () => fetchMartWeeklyTrend(8), staleTime: 300_000 });
  const { data: catRank = [], isLoading: cL } = useQuery<CatRank[]>({ queryKey: ['cat-ranking'], queryFn: fetchCategoryRanking, staleTime: 300_000 });
  const { data: rfm = [], isLoading: rL } = useQuery<RFM[]>({ queryKey: ['mart-rfm'], queryFn: fetchMartRFM, staleTime: 300_000 });
  const { data: assoc = [] } = useQuery<Assoc[]>({ queryKey: ['mart-assoc'], queryFn: () => fetchMartAssociation(5), staleTime: 300_000 });

  const wData = [...weekly].sort((a, b) => new Date(a.week).getTime() - new Date(b.week).getTime());
  const totalUsers = rfm.reduce((s, r) => s + (r.user_count ?? 0), 0);
  const bestShare = ws?.best_category_revenue && ws?.total_week_revenue
    ? ((ws.best_category_revenue / ws.total_week_revenue) * 100).toFixed(1)
    : null;

  return (
    <div>
      {/* Weekly KPIs */}
      {wsL ? (
        <div className="kpi-row-3">{[0, 1, 2].map(i => <div key={i} className="kpi"><Sk h={56} /></div>)}</div>
      ) : ws && ws.revenue ? (
        <div className="kpi-row-3">
          <div className="kpi">
            <div className="kpi-label"><TrendingUp size={13} /> Weekly Revenue</div>
            <div className="kpi-main">
              <span className="kpi-value">{krw(ws.revenue)}</span>
              <Trend value={ws.wow_revenue_pct} />
            </div>
            <div className="kpi-sub">이번 주 누적</div>
          </div>
          <div className="kpi b-blue">
            <div className="kpi-label"><BarChart3 size={13} /> Weekly Orders</div>
            <div className="kpi-main">
              <span className="kpi-value">{fN(ws.orders)}</span>
              <Trend value={ws.wow_orders_pct} />
            </div>
            <div className="kpi-sub">이번 주 누적</div>
          </div>
          <div className="kpi b-yellow">
            <div className="kpi-label"><TrendingUp size={13} /> Best Category</div>
            <div className="kpi-main">
              <span className="kpi-value" style={{ fontSize: 22 }}>{ws.best_category ?? '--'}</span>
            </div>
            <div className="kpi-sub">{ws.best_category_revenue ? `${krw(ws.best_category_revenue)}` : ''}{bestShare ? ` (${bestShare}%)` : ''}</div>
          </div>
        </div>
      ) : null}

      {/* Weekly Trend */}
      <div className="panel">
        <div className="panel-hd"><TrendingUp size={14} /><span className="panel-title">Weekly Trend</span><span className="panel-meta">8w · revenue + orders</span></div>
        <div className="panel-body">
          {wL ? <Sk /> : wData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={wData}>
                <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" vertical={false} />
                <XAxis dataKey="week" tick={AX} tickLine={false} axisLine={false} tickFormatter={fD} />
                <YAxis yAxisId="l" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => krw(v)} />
                <YAxis yAxisId="r" orientation="right" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => fN(v)} />
                <Tooltip {...TIP} formatter={(v: number | undefined, name?: string) => name === '매출' ? [krw(v ?? 0), name] : [fN(v ?? 0), name ?? '']} labelFormatter={d => { try { return `${new Date(d as string).toLocaleDateString('ko-KR')} 주차`; } catch { return String(d); } }} />
                <Line yAxisId="l" type="monotone" dataKey="revenue" stroke="#22C55E" strokeWidth={2} name="매출" dot={{ r: 3, fill: '#22C55E', stroke: '#0E0E0E', strokeWidth: 2 }} />
                <Line yAxisId="r" type="monotone" dataKey="orders" stroke="#3B82F6" strokeWidth={2} name="주문수" dot={{ r: 3, fill: '#3B82F6', stroke: '#0E0E0E', strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="empty">데이터 없음</div>}
        </div>
      </div>

      {/* Category Ranking + RFM */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd"><BarChart3 size={14} /><span className="panel-title">Category Ranking</span><span className="panel-meta">WoW comparison</span></div>
          <div className="panel-body">
            {cL ? <Sk h={240} /> : catRank.length > 0 ? (
              <ResponsiveContainer width="100%" height={Math.max(200, catRank.length * 36)}>
                <BarChart data={catRank} layout="vertical" margin={{ left: 4 }}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" horizontal={false} />
                  <XAxis type="number" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => krw(v)} />
                  <YAxis type="category" dataKey="category" width={80} tick={{ fill: '#808080', fontSize: 11, fontFamily: "'IBM Plex Sans'" }} tickLine={false} axisLine={false} />
                  <Tooltip {...TIP} formatter={(v: number | undefined) => [krw(v ?? 0), '매출']} />
                  <Bar dataKey="revenue" name="매출" radius={[0, 4, 4, 0]} barSize={20}>
                    {catRank.map((_, i) => <Cell key={i} fill={CL[i % CL.length]} fillOpacity={0.8} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
            {/* WoW badges */}
            {catRank.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {catRank.slice(0, 5).map(c => (
                  <span key={c.category} style={{ fontSize: 10, color: 'var(--t2)', fontFamily: 'var(--mono)' }}>
                    {c.category} {c.wow_pct != null ? (
                      <span style={{ color: c.wow_pct >= 0 ? 'var(--accent)' : 'var(--red)', fontWeight: 600 }}>
                        {c.wow_pct >= 0 ? '↑' : '↓'}{Math.abs(c.wow_pct)}%
                      </span>
                    ) : ''}
                    {c.share_pct ? ` (${c.share_pct}%)` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd"><Users size={14} /><span className="panel-title">RFM Segments</span><span className="panel-meta">{totalUsers.toLocaleString()} users</span></div>
          <div className="panel-body">
            {rL ? <Sk h={240} /> : rfm.length > 0 ? (
              <ResponsiveContainer width="100%" height={Math.max(200, rfm.length * 44)}>
                <BarChart data={rfm} layout="vertical" margin={{ left: 4 }}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" horizontal={false} />
                  <XAxis type="number" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => fN(v)} />
                  <YAxis type="category" dataKey="segment" width={72} tick={{ fill: '#808080', fontSize: 11, fontFamily: "'IBM Plex Sans'" }} tickLine={false} axisLine={false} />
                  <Tooltip {...TIP} formatter={(v: number | undefined) => [(v ?? 0).toLocaleString(), '고객 수']} />
                  <Bar dataKey="user_count" name="고객 수" radius={[0, 4, 4, 0]} barSize={22}>
                    {rfm.map((_, i) => <Cell key={i} fill={CL[i % CL.length]} fillOpacity={0.8} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
            {/* segment share */}
            {totalUsers > 0 && rfm.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {rfm.map((r, i) => (
                  <span key={r.segment} style={{ fontSize: 10, fontFamily: 'var(--mono)' }}>
                    <span style={{ color: CL[i % CL.length] }}>●</span>{' '}
                    <span style={{ color: 'var(--t2)' }}>{r.segment} {((r.user_count / totalUsers) * 100).toFixed(1)}%</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Association Rules */}
      {assoc.length > 0 && (
        <div className="panel">
          <div className="panel-hd"><Link2 size={14} /><span className="panel-title">Product Associations</span><span className="panel-meta">Top 5</span></div>
          <div className="panel-body flush">
            <table className="tbl">
              <thead><tr><th>연관 패턴</th><th className="r">Confidence</th><th className="r">Lift</th></tr></thead>
              <tbody>
                {assoc.map((r, i) => (
                  <tr key={i}>
                    <td className="name" style={{ fontSize: 12 }}>
                      {r.antecedents} → {r.consequents}
                      <div style={{ fontSize: 10, color: 'var(--t3)', marginTop: 2 }}>
                        {r.lift > 2 ? `함께 구매할 확률 ${r.lift.toFixed(1)}배 높음` : `약한 연관 (${r.lift.toFixed(1)}x)`}
                      </div>
                    </td>
                    <td className="r">{((r.confidence ?? 0) * 100).toFixed(1)}%</td>
                    <td className="r" style={{ color: r.lift > 2 ? 'var(--accent)' : 'var(--t2)', fontWeight: r.lift > 2 ? 600 : 400 }}>
                      {r.lift.toFixed(2)}x
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
