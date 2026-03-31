import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ReferenceLine,
} from 'recharts';
import { DollarSign, ShoppingCart, TrendingUp, Clock, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import {
  fetchSummary, fetchHourlyTraffic, fetchHourlyThroughput,
  fetchDailyTrend, fetchFunnelTrend,
} from '../api/client';

/* ── chart shared ── */
const CL = ['#22C55E', '#3B82F6', '#A855F7', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899', '#F97316'];
const TIP = {
  contentStyle: { backgroundColor: '#0F0F0F', border: '1px solid #303030', borderRadius: 4, fontSize: 11, fontFamily: "'IBM Plex Mono',monospace", padding: '6px 10px' },
  itemStyle: { color: '#E2E2E2', fontSize: 11, fontFamily: "'IBM Plex Mono',monospace" },
};
const AX = { fill: '#4A4A4A', fontSize: 10, fontFamily: "'IBM Plex Mono',monospace" };

/* ── formatters ── */
const fmt = (n: number | null | undefined) => {
  if (n == null) return '--';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString();
};
const krw = (n: number | null | undefined) => {
  if (n == null) return '--';
  if (n >= 1e12) return `${(n / 1e12).toFixed(1)}조`;
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}억`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(0)}만`;
  return `₩${n.toLocaleString()}`;
};
const fresh = (s: number | null | undefined) => {
  if (s == null) return '--';
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
};
const hm = (t: string) => { try { return new Date(t).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }); } catch { return t; } };

/* ── trend badge ── */
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

/* ── sparkline ── */
function Spark({ data, dataKey }: { data: { date: string }[]; dataKey: string }) {
  if (!data || data.length < 2) return null;
  return (
    <div className="sparkline">
      <ResponsiveContainer width="100%" height={32}>
        <LineChart data={data}>
          <Line type="monotone" dataKey={dataKey} stroke="#22C55E" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Sk({ h = 220 }: { h?: number }) {
  return <div className="sk" style={{ width: '100%', height: h }} />;
}

/* ── page ── */
export default function OverviewPage() {
  const { data: sum, isLoading: sumL } = useQuery({ queryKey: ['summary'], queryFn: fetchSummary, refetchInterval: 30_000 });
  const { data: trend = [] } = useQuery<{ date: string; total_revenue: number; total_orders: number; avg_order_value: number; dod_pct: number | null }[]>({ queryKey: ['daily-trend'], queryFn: fetchDailyTrend, refetchInterval: 60_000 });
  const { data: traffic = [], isLoading: trL } = useQuery<Record<string, unknown>[]>({ queryKey: ['hourly-traffic'], queryFn: fetchHourlyTraffic, refetchInterval: 30_000 });
  const { data: thru = [], isLoading: thL } = useQuery<{ hour: string; total_orders: number }[]>({ queryKey: ['hourly-throughput'], queryFn: fetchHourlyThroughput, refetchInterval: 30_000 });
  const { data: funnelTrend = [], isLoading: ftL } = useQuery<{ date: string; sessions: number; views: number; carts: number; purchases: number; cart_rate: number; purchase_rate: number; overall_cvr: number }[]>({ queryKey: ['funnel-trend'], queryFn: fetchFunnelTrend, refetchInterval: 60_000 });

  const cats = Array.from(new Set(traffic.flatMap(r => Object.keys(r).filter(k => k !== 'time'))));
  const major = cats.filter(c => traffic.reduce((s, r) => s + ((r[c] as number) ?? 0), 0) > 1000);
  const avg = thru.length > 0 ? Math.round(thru.reduce((s, r) => s + (r.total_orders ?? 0), 0) / thru.length) : 0;

  // latest funnel day
  const latestFunnel = funnelTrend.length > 0 ? funnelTrend[funnelTrend.length - 1] : null;

  return (
    <div>
      {/* KPI cards */}
      {sumL ? (
        <div className="kpi-row">{[0, 1, 2, 3].map(i => <div key={i} className="kpi"><Sk h={56} /></div>)}</div>
      ) : (
        <div className="kpi-row">
          <div className="kpi">
            <div className="kpi-label"><DollarSign size={13} /> Revenue (24h)</div>
            <div className="kpi-main">
              <span className="kpi-value">{krw(sum?.today_revenue)}</span>
              <Trend value={sum?.dod_revenue_pct} />
            </div>
            <Spark data={trend} dataKey="total_revenue" />
          </div>
          <div className="kpi b-blue">
            <div className="kpi-label"><ShoppingCart size={13} /> Orders (24h)</div>
            <div className="kpi-main">
              <span className="kpi-value">{fmt(sum?.today_events)}</span>
              <Trend value={sum?.dod_orders_pct} />
            </div>
            <Spark data={trend} dataKey="total_orders" />
          </div>
          <div className="kpi b-yellow">
            <div className="kpi-label"><TrendingUp size={13} /> Avg Order Value</div>
            <div className="kpi-main">
              <span className="kpi-value">{krw(sum?.avg_order_value)}</span>
            </div>
            <Spark data={trend} dataKey="avg_order_value" />
          </div>
          <div className="kpi b-cyan">
            <div className="kpi-label"><Clock size={13} /> Freshness</div>
            <div className="kpi-main">
              <span className="kpi-value green">{fresh(sum?.data_freshness_sec)}</span>
            </div>
            <div className="kpi-sub">최신 이벤트 기준{sum?.top_category ? ` · 베스트: ${sum.top_category}` : ''}</div>
          </div>
        </div>
      )}

      {/* charts */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd"><Activity size={14} /><span className="panel-title">Category Traffic</span><span className="panel-meta">24h</span></div>
          <div className="panel-body">
            {trL ? <Sk /> : traffic.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={traffic}>
                  <defs>{major.map((c, i) => (
                    <linearGradient key={c} id={`g-${c}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CL[i % CL.length]} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={CL[i % CL.length]} stopOpacity={0} />
                    </linearGradient>
                  ))}</defs>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" vertical={false} />
                  <XAxis dataKey="time" tick={AX} tickLine={false} axisLine={false} tickFormatter={hm} />
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmt(v)} />
                  <Tooltip {...TIP} labelFormatter={t => { try { return new Date(t as string).toLocaleString('ko-KR'); } catch { return String(t); } }} />
                  {major.map((c, i) => (
                    <Area key={c} type="monotone" dataKey={c} stackId="1" stroke={CL[i % CL.length]} strokeWidth={1.5} fill={`url(#g-${c})`} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
        <div className="panel">
          <div className="panel-hd"><TrendingUp size={14} /><span className="panel-title">Hourly Throughput</span><span className="panel-meta">avg {fmt(avg)}/h</span></div>
          <div className="panel-body">
            {thL ? <Sk /> : thru.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={thru}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" vertical={false} />
                  <XAxis dataKey="hour" tick={AX} tickLine={false} axisLine={false} tickFormatter={hm} />
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmt(v)} />
                  <Tooltip {...TIP} formatter={(v: number | undefined) => [(v ?? 0).toLocaleString(), '주문']} labelFormatter={h => { try { return new Date(h as string).toLocaleString('ko-KR'); } catch { return String(h); } }} />
                  {avg > 0 && <ReferenceLine y={avg} stroke="#F59E0B" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: `avg ${fmt(avg)}`, fill: '#F59E0B', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} />}
                  <Line type="monotone" dataKey="total_orders" stroke="#22C55E" strokeWidth={2} dot={false} activeDot={{ r: 3, fill: '#22C55E', stroke: '#0E0E0E', strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
      </div>

      {/* Funnel with rates */}
      <div className="panel">
        <div className="panel-hd">
          <span className="panel-title">Conversion Funnel</span>
          {latestFunnel && <span className="panel-meta" style={{ color: 'var(--accent)', fontWeight: 600 }}>CVR {latestFunnel.overall_cvr}%</span>}
        </div>
        <div className="panel-body">
          {ftL ? <Sk h={100} /> : latestFunnel ? (
            <>
              {[
                { step: 'Views', count: latestFunnel.views, color: '#22C55E', rate: null },
                { step: '→ Cart', count: latestFunnel.carts, color: '#3B82F6', rate: latestFunnel.cart_rate },
                { step: '→ Purchase', count: latestFunnel.purchases, color: '#A855F7', rate: latestFunnel.purchase_rate },
              ].map(f => {
                const pct = latestFunnel.views > 0 ? (f.count / latestFunnel.views) * 100 : 0;
                return (
                  <div className="funnel-step" key={f.step}>
                    <span className="funnel-lbl">{f.step}</span>
                    <div className="funnel-bar">
                      <div className="funnel-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg,${f.color},${f.color}bb)`, boxShadow: `0 0 8px ${f.color}22` }} />
                    </div>
                    <span className="funnel-val">{fmt(f.count)}</span>
                    <span className="funnel-rate">{f.rate != null ? `${f.rate}%` : ''}</span>
                  </div>
                );
              })}
              {/* CVR trend sparkline */}
              {funnelTrend.length > 2 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 10, color: 'var(--t3)', marginBottom: 4 }}>7일 CVR 추이</div>
                  <div style={{ height: 36 }}>
                    <ResponsiveContainer width="100%" height={36}>
                      <LineChart data={funnelTrend}>
                        <Line type="monotone" dataKey="overall_cvr" stroke="#A855F7" strokeWidth={1.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          ) : <div className="empty">데이터 없음</div>}
        </div>
      </div>
    </div>
  );
}
