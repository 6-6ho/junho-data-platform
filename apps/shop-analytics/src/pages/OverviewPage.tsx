import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ReferenceLine,
} from 'recharts';
import { Layers, Zap, DollarSign, Clock, Activity, TrendingUp } from 'lucide-react';
import {
  fetchSummary, fetchHourlyTraffic, fetchHourlyThroughput, fetchFunnel,
} from '../api/client';

/* ── helpers ─────────────────────────────── */

const CHART_COLORS = ['#22C55E', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899', '#F97316'];

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: '#1E1E1E',
    border: '1px solid #2A2A2A',
    borderRadius: '6px',
    fontSize: '12px',
  },
  itemStyle: { color: '#fff', fontSize: '12px' },
};

const fmt = (n: number | null | undefined): string => {
  if (n == null) return '--';
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
};

const fmtKRW = (n: number | null | undefined): string => {
  if (n == null) return '--';
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
  if (n >= 10_000) return `${(n / 10_000).toFixed(0)}만`;
  return `₩${n.toLocaleString()}`;
};

const fmtFresh = (sec: number | null | undefined): string => {
  if (sec == null) return '--';
  if (sec < 60) return `${sec}초`;
  if (sec < 3600) return `${Math.floor(sec / 60)}분`;
  return `${Math.floor(sec / 3600)}시간`;
};

const fmtTime = (t: string) => {
  try {
    return new Date(t).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return t;
  }
};

/* ── component ───────────────────────────── */

export default function OverviewPage() {
  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    refetchInterval: 30_000,
  });

  const { data: hourlyTraffic = [] } = useQuery<Record<string, unknown>[]>({
    queryKey: ['hourly-traffic'],
    queryFn: fetchHourlyTraffic,
    refetchInterval: 30_000,
  });

  const { data: hourlyThroughput = [] } = useQuery<{ hour: string; total_orders: number }[]>({
    queryKey: ['hourly-throughput'],
    queryFn: fetchHourlyThroughput,
    refetchInterval: 30_000,
  });

  const { data: funnelRaw } = useQuery<{
    page_view: number;
    add_to_cart: number;
    purchase: number;
    conversion_rate: number;
  }>({
    queryKey: ['funnel'],
    queryFn: fetchFunnel,
    refetchInterval: 30_000,
  });

  /* derive categories from traffic data (dynamic keys) */
  const categories = Array.from(
    new Set(
      hourlyTraffic.flatMap((row) =>
        Object.keys(row).filter((k) => k !== 'time'),
      ),
    ),
  );

  /* major categories only (hide tiny ones like "Accessories", "Shoes" etc.) */
  const majorCategories = categories.filter((cat) => {
    const total = hourlyTraffic.reduce(
      (sum, row) => sum + ((row[cat] as number) ?? 0),
      0,
    );
    return total > 1000;
  });

  /* throughput average */
  const avgOrders =
    hourlyThroughput.length > 0
      ? Math.round(
          hourlyThroughput.reduce((s, r) => s + (r.total_orders ?? 0), 0) /
            hourlyThroughput.length,
        )
      : 0;

  /* funnel steps */
  const funnel = funnelRaw
    ? [
        { step: '페이지 조회', count: funnelRaw.page_view ?? 0, color: '#22C55E' },
        { step: '장바구니', count: funnelRaw.add_to_cart ?? 0, color: '#3B82F6' },
        { step: '구매', count: funnelRaw.purchase ?? 0, color: '#8B5CF6' },
      ]
    : [];
  const maxFunnel = funnel.length > 0 ? Math.max(...funnel.map((f) => f.count)) : 1;

  return (
    <div>
      {/* ── KPI ── */}
      <div className="kpi-grid">
        <div className="stat-card">
          <div className="stat-label"><Layers size={14} /> 총 처리 이벤트</div>
          <div className="stat-value">{fmt(summary?.total_events)}</div>
          <div className="stat-sub">전체 누적</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><Zap size={14} /> 24h 처리량</div>
          <div className="stat-value accent">{fmt(summary?.today_events)}</div>
          <div className="stat-sub">오늘 이벤트</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><DollarSign size={14} /> 24h 매출</div>
          <div className="stat-value">{fmtKRW(summary?.today_revenue)}</div>
          <div className="stat-sub">오늘 매출</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><Clock size={14} /> 데이터 신선도</div>
          <div className="stat-value accent">{fmtFresh(summary?.data_freshness_sec)}</div>
          <div className="stat-sub">최신 이벤트 기준</div>
        </div>
      </div>

      {/* ── Charts 2-col ── */}
      <div className="chart-grid">
        {/* Category Traffic AreaChart */}
        <div className="card">
          <div className="card-title">
            <Activity size={16} />
            카테고리별 트래픽 (24h)
          </div>
          {hourlyTraffic.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={hourlyTraffic}>
                <defs>
                  {majorCategories.map((cat, i) => (
                    <linearGradient key={cat} id={`grad-${cat}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={fmtTime}
                />
                <YAxis
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => fmt(v)}
                />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  labelFormatter={(t) => {
                    try { return new Date(t as string).toLocaleString('ko-KR'); }
                    catch { return String(t); }
                  }}
                />
                {majorCategories.map((cat, i) => (
                  <Area
                    key={cat}
                    type="monotone"
                    dataKey={cat}
                    stackId="1"
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    strokeWidth={1.5}
                    fill={`url(#grad-${cat})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">데이터 없음</div>
          )}
        </div>

        {/* Throughput LineChart */}
        <div className="card">
          <div className="card-title">
            <TrendingUp size={16} />
            시간별 처리량 (24h)
          </div>
          {hourlyThroughput.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={hourlyThroughput}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="hour"
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={fmtTime}
                />
                <YAxis
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => fmt(v)}
                />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(value: number | undefined) => [
                    (value ?? 0).toLocaleString(),
                    '주문 건수',
                  ]}
                  labelFormatter={(h) => {
                    try { return new Date(h as string).toLocaleString('ko-KR'); }
                    catch { return String(h); }
                  }}
                />
                {avgOrders > 0 && (
                  <ReferenceLine
                    y={avgOrders}
                    stroke="#F59E0B"
                    strokeDasharray="5 5"
                    label={{ value: `평균 ${fmt(avgOrders)}`, fill: '#F59E0B', fontSize: 11 }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="total_orders"
                  stroke="#22C55E"
                  strokeWidth={2}
                  name="주문 건수"
                  dot={{ r: 2, fill: '#22C55E' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">데이터 없음</div>
          )}
        </div>
      </div>

      {/* ── Funnel ── */}
      {funnel.length > 0 && (
        <div className="card">
          <div className="card-title">전환 퍼널</div>
          <div className="funnel-bar-wrapper">
            {funnel.map((step, idx) => {
              const pct = maxFunnel > 0 ? (step.count / maxFunnel) * 100 : 0;
              const convRate =
                idx > 0 && funnel[idx - 1].count > 0
                  ? ((step.count / funnel[idx - 1].count) * 100).toFixed(1)
                  : null;
              return (
                <div className="funnel-row" key={step.step}>
                  <span className="funnel-label">{step.step}</span>
                  <div className="funnel-track">
                    <div
                      className="funnel-fill"
                      style={{
                        width: `${pct}%`,
                        background: step.color,
                      }}
                    />
                  </div>
                  <span className="funnel-value">{fmt(step.count)}</span>
                  <span className="funnel-pct">{convRate ? `${convRate}%` : ''}</span>
                </div>
              );
            })}
          </div>
          {funnelRaw?.conversion_rate != null && (
            <div style={{ marginTop: 12, fontSize: 13, color: '#A3A3A3' }}>
              전체 전환율: <span style={{ color: '#22C55E', fontWeight: 600 }}>{funnelRaw.conversion_rate.toFixed(2)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
