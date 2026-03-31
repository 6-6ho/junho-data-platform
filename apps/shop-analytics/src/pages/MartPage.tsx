import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell,
} from 'recharts';
import { CalendarDays, Users, Link2, TrendingUp } from 'lucide-react';
import {
  fetchMartDailySales, fetchMartRFM, fetchMartAssociation, fetchMartWeeklyTrend,
} from '../api/client';

/* ── helpers ─────────────────────────────── */

const CHART_COLORS = ['#22C55E', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444'];

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: '#1E1E1E',
    border: '1px solid #2A2A2A',
    borderRadius: '6px',
    fontSize: '12px',
  },
  itemStyle: { color: '#fff', fontSize: '12px' },
};

const fmtKRW = (n: number | null | undefined): string => {
  if (n == null) return '--';
  if (n >= 1_000_000_000_000) return `${(n / 1_000_000_000_000).toFixed(1)}조`;
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
  if (n >= 10_000) return `${(n / 10_000).toFixed(0)}만`;
  return `₩${n.toLocaleString()}`;
};

const fmtNum = (n: number | null | undefined): string => {
  if (n == null) return '--';
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
};

const fmtDate = (d: string) => {
  try {
    return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  } catch {
    return d;
  }
};

/* ── types (exact API shapes) ────────────── */

interface DailySalesRow {
  date: string;
  category: string;
  revenue: number;
  orders: number;
  avg_value: number;
}

interface RFMRow {
  segment: string;
  user_count: number;
}

interface AssociationRow {
  antecedents: string;
  consequents: string;
  confidence: number;
  lift: number;
  support: number;
}

interface WeeklyRow {
  week: string;
  revenue: number;
  orders: number;
}

/* ── component ───────────────────────────── */

export default function MartPage() {
  const { data: dailySales = [] } = useQuery<DailySalesRow[]>({
    queryKey: ['mart-daily-sales'],
    queryFn: () => fetchMartDailySales(7),
    staleTime: 300_000,
  });

  const { data: rfm = [] } = useQuery<RFMRow[]>({
    queryKey: ['mart-rfm'],
    queryFn: fetchMartRFM,
    staleTime: 300_000,
  });

  const { data: association = [] } = useQuery<AssociationRow[]>({
    queryKey: ['mart-association'],
    queryFn: () => fetchMartAssociation(10),
    staleTime: 300_000,
  });

  const { data: weeklyTrend = [] } = useQuery<WeeklyRow[]>({
    queryKey: ['mart-weekly-trend'],
    queryFn: () => fetchMartWeeklyTrend(8),
    staleTime: 300_000,
  });

  /* group daily sales by date */
  const dateGroups = new Map<string, DailySalesRow[]>();
  dailySales.forEach((row) => {
    const existing = dateGroups.get(row.date) || [];
    existing.push(row);
    dateGroups.set(row.date, existing);
  });
  const sortedDates = Array.from(dateGroups.keys()).sort().reverse();

  /* sort weekly trend chronologically for chart */
  const weeklyChartData = [...weeklyTrend].sort(
    (a, b) => new Date(a.week).getTime() - new Date(b.week).getTime(),
  );

  return (
    <div>
      {/* ── Daily Sales Table ── */}
      <div className="card" style={{ padding: 0 }}>
        <div className="card-title" style={{ padding: '20px 20px 0 20px' }}>
          <CalendarDays size={16} />
          일별 매출 (카테고리별)
          <span className="card-subtitle">최근 7일</span>
        </div>
        <div style={{ padding: '12px 0 0 0', overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>날짜</th>
                <th>카테고리</th>
                <th className="right">매출</th>
                <th className="right">주문수</th>
                <th className="right">객단가</th>
              </tr>
            </thead>
            <tbody>
              {sortedDates.length > 0 ? (
                sortedDates.map((date) => {
                  const rows = dateGroups.get(date)!;
                  return rows.map((row, idx) => (
                    <tr key={`${date}-${row.category}`}>
                      {idx === 0 && (
                        <td
                          className="primary"
                          rowSpan={rows.length}
                          style={{ verticalAlign: 'top', fontWeight: 600 }}
                        >
                          {(() => {
                            try {
                              return new Date(date).toLocaleDateString('ko-KR', {
                                month: 'short',
                                day: 'numeric',
                                weekday: 'short',
                              });
                            } catch {
                              return date;
                            }
                          })()}
                        </td>
                      )}
                      <td>{row.category}</td>
                      <td className="right">{fmtKRW(row.revenue ?? 0)}</td>
                      <td className="right">{fmtNum(row.orders ?? 0)}</td>
                      <td className="right">{fmtKRW(row.avg_value ?? 0)}</td>
                    </tr>
                  ));
                })
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: '#666', padding: 40 }}>
                    데이터 없음
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 2-col: RFM + Association ── */}
      <div className="chart-grid">
        {/* RFM Distribution BarChart */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-title">
            <Users size={16} />
            RFM 세그먼트 분포
          </div>
          {rfm.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={rfm} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 11 }}
                  tickLine={false}
                  tickFormatter={(v: number) => fmtNum(v)}
                />
                <YAxis
                  type="category"
                  dataKey="segment"
                  stroke="#666"
                  tick={{ fill: '#A3A3A3', fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={70}
                />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(value: number | undefined) => [(value ?? 0).toLocaleString(), '고객 수']}
                />
                <Bar dataKey="user_count" name="고객 수" radius={[0, 4, 4, 0]}>
                  {rfm.map((_entry, idx) => (
                    <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">데이터 없음</div>
          )}
        </div>

        {/* Product Association Table */}
        <div className="card" style={{ marginBottom: 0, padding: 0 }}>
          <div className="card-title" style={{ padding: '20px 20px 0 20px' }}>
            <Link2 size={16} />
            연관 규칙
            <span className="card-subtitle">Top 10</span>
          </div>
          <div style={{ padding: '12px 0 0 0', overflow: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>선행 상품</th>
                  <th>후행 상품</th>
                  <th className="right">Confidence</th>
                  <th className="right">Lift</th>
                </tr>
              </thead>
              <tbody>
                {association.length > 0 ? (
                  association.map((row, idx) => (
                    <tr key={idx}>
                      <td style={{ fontSize: 12 }}>{row.antecedents}</td>
                      <td style={{ fontSize: 12 }}>{row.consequents}</td>
                      <td className="right">{((row.confidence ?? 0) * 100).toFixed(1)}%</td>
                      <td
                        className="right"
                        style={{
                          color: (row.lift ?? 0) > 2 ? '#22C55E' : '#A3A3A3',
                          fontWeight: (row.lift ?? 0) > 2 ? 600 : 400,
                        }}
                      >
                        {(row.lift ?? 0).toFixed(2)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: '#666', padding: 40 }}>
                      데이터 없음
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Weekly Sales Trend ── */}
      <div className="card">
        <div className="card-title">
          <TrendingUp size={16} />
          주별 매출 추이
          <span className="card-subtitle">최근 8주</span>
        </div>
        {weeklyChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={weeklyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="week"
                stroke="#666"
                tick={{ fill: '#666', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={fmtDate}
              />
              <YAxis
                yAxisId="left"
                stroke="#666"
                tick={{ fill: '#666', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => fmtKRW(v)}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#666"
                tick={{ fill: '#666', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => fmtNum(v)}
              />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(value: number | undefined, name?: string) => {
                  if (name === '매출') return [fmtKRW(value ?? 0), name];
                  return [fmtNum(value ?? 0), name ?? ''];
                }}
                labelFormatter={(d) => {
                  try { return `${new Date(d as string).toLocaleDateString('ko-KR')} 주차`; }
                  catch { return String(d); }
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="revenue"
                stroke="#22C55E"
                strokeWidth={2}
                name="매출"
                dot={{ r: 4, fill: '#22C55E' }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="orders"
                stroke="#3B82F6"
                strokeWidth={2}
                name="주문수"
                dot={{ r: 3, fill: '#3B82F6' }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">데이터 없음</div>
        )}
      </div>
    </div>
  );
}
