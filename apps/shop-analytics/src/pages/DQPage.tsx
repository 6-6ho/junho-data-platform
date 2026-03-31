import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Shield, AlertTriangle, GitCompareArrows } from 'lucide-react';
import {
  fetchDQScoreTrend, fetchDQReconciliation, fetchDQAnomalyRawCount,
  fetchDQCategoryHealth, fetchDQRulesSummary,
} from '../api/client';

/* ── helpers ─────────────────────────────── */

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: '#1E1E1E',
    border: '1px solid #2A2A2A',
    borderRadius: '6px',
    fontSize: '12px',
  },
  itemStyle: { color: '#fff', fontSize: '12px' },
};

const DIMENSION_BADGE: Record<string, string> = {
  Completeness: 'badge-blue',
  Validity: 'badge-green',
  Timeliness: 'badge-yellow',
  Consistency: 'badge-purple',
};

const LAYER_BADGE: Record<string, string> = {
  Stream: 'badge-blue',
  ETL: 'badge-purple',
};

const fmtDate = (d: string) => {
  try {
    return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  } catch {
    return d;
  }
};

const fmtTime = (h: string) => {
  try {
    return new Date(h).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return h;
  }
};

/* ── types (matching exact API shapes) ──── */

interface ScoreTrendRow {
  date: string;
  completeness_score: number;
  validity_score: number;
  timeliness_score: number;
  total_score: number;
}

interface ReconciliationRow {
  hour: string;
  category_total: number;
  payment_total: number;
  diff_pct: number;
}

interface CategoryHealthRow {
  category: string;
  event_count: number;
  purchase_count: number;
  total_revenue: number;
}

interface RuleRow {
  dimension: string;
  rule_name: string;
  target: string;
  layer: string;
  trigger_count_7d: number;
  status: string;
}

/* ── component ───────────────────────────── */

export default function DQPage() {
  const { data: scoreTrend = [] } = useQuery<ScoreTrendRow[]>({
    queryKey: ['dq-score-trend'],
    queryFn: fetchDQScoreTrend,
    refetchInterval: 60_000,
  });

  const { data: reconciliation = [] } = useQuery<ReconciliationRow[]>({
    queryKey: ['dq-reconciliation'],
    queryFn: fetchDQReconciliation,
    refetchInterval: 60_000,
  });

  const { data: anomalyRaw } = useQuery<{ total: number; breakdown: Record<string, number> }>({
    queryKey: ['dq-anomaly-raw-count'],
    queryFn: fetchDQAnomalyRawCount,
    refetchInterval: 60_000,
  });

  const { data: categoryHealth = [] } = useQuery<CategoryHealthRow[]>({
    queryKey: ['dq-category-health'],
    queryFn: fetchDQCategoryHealth,
    refetchInterval: 60_000,
  });

  const { data: rules = [] } = useQuery<RuleRow[]>({
    queryKey: ['dq-rules-summary'],
    queryFn: fetchDQRulesSummary,
    refetchInterval: 60_000,
  });

  /* KPI */
  const latestScore =
    scoreTrend.length > 0 ? scoreTrend[scoreTrend.length - 1].total_score : null;

  const anomalyCount = anomalyRaw?.total ?? 0;

  const maxDiff =
    reconciliation.length > 0
      ? Math.max(...reconciliation.map((r) => r.diff_pct ?? 0))
      : 0;

  return (
    <div>
      {/* ── KPI ── */}
      <div className="kpi-grid-3">
        <div className="stat-card">
          <div className="stat-label"><Shield size={14} /> DQ 종합 스코어</div>
          <div
            className={`stat-value ${
              latestScore !== null && latestScore >= 90 ? 'accent' : latestScore !== null ? 'danger' : ''
            }`}
          >
            {latestScore !== null ? `${latestScore}점` : '--'}
          </div>
          <div className="stat-sub">최신 일자 기준</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><AlertTriangle size={14} /> 이상 격리 수</div>
          <div className={`stat-value ${anomalyCount > 0 ? 'danger' : ''}`}>
            {anomalyCount}건
          </div>
          <div className="stat-sub">anomaly_raw 테이블 기준</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><GitCompareArrows size={14} /> 최대 불일치율</div>
          <div className={`stat-value ${maxDiff > 5 ? 'danger' : ''}`}>
            {maxDiff.toFixed(1)}%
          </div>
          <div className="stat-sub">카테고리 vs 결제수단 교차검증</div>
        </div>
      </div>

      {/* ── DQ Score Trend ── */}
      <div className="card">
        <div className="card-title">
          <Shield size={16} />
          DQ 스코어 트렌드 (14일)
          <span className="card-subtitle">C / V / T</span>
        </div>
        {scoreTrend.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={scoreTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="date"
                stroke="#666"
                tick={{ fill: '#666', fontSize: 11 }}
                tickLine={false}
                tickFormatter={fmtDate}
              />
              <YAxis
                domain={[0, 100]}
                stroke="#666"
                tick={{ fill: '#666', fontSize: 11 }}
                tickLine={false}
              />
              <Tooltip {...TOOLTIP_STYLE} />
              <ReferenceLine
                y={90}
                stroke="#EF4444"
                strokeDasharray="5 5"
                label={{ value: '임계치 90', fill: '#EF4444', fontSize: 11 }}
              />
              <Line type="monotone" dataKey="completeness_score" stroke="#3B82F6" strokeWidth={2} name="완전성 (C)" dot={false} />
              <Line type="monotone" dataKey="validity_score" stroke="#22C55E" strokeWidth={2} name="유효성 (V)" dot={false} />
              <Line type="monotone" dataKey="timeliness_score" stroke="#F59E0B" strokeWidth={2} name="적시성 (T)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">데이터 없음</div>
        )}
      </div>

      {/* ── 2-col: Reconciliation + Category Health ── */}
      <div className="chart-grid">
        {/* Reconciliation diff_pct chart */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-title">
            <GitCompareArrows size={16} />
            교차검증 불일치율 (24h)
          </div>
          {reconciliation.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={reconciliation}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="hour"
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 10 }}
                  tickLine={false}
                  tickFormatter={fmtTime}
                />
                <YAxis
                  stroke="#666"
                  tick={{ fill: '#666', fontSize: 11 }}
                  tickLine={false}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(1)}%`, '불일치율']}
                />
                <ReferenceLine
                  y={5}
                  stroke="#EF4444"
                  strokeDasharray="5 5"
                  label={{ value: '임계치 5%', fill: '#EF4444', fontSize: 11 }}
                />
                <Line
                  type="monotone"
                  dataKey="diff_pct"
                  stroke="#8B5CF6"
                  strokeWidth={2}
                  name="불일치율"
                  dot={{ r: 3, fill: '#8B5CF6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">데이터 없음</div>
          )}
        </div>

        {/* Category Health Table */}
        <div className="card" style={{ marginBottom: 0, padding: 0 }}>
          <div className="card-title" style={{ padding: '20px 20px 0 20px' }}>
            카테고리 건강도
          </div>
          <div style={{ padding: '12px 0 0 0', overflow: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>카테고리</th>
                  <th className="right">이벤트</th>
                  <th className="right">구매</th>
                  <th className="right">매출</th>
                </tr>
              </thead>
              <tbody>
                {categoryHealth.length > 0 ? (
                  categoryHealth.map((row) => (
                    <tr key={row.category}>
                      <td className="primary">{row.category}</td>
                      <td className="right">{(row.event_count ?? 0).toLocaleString()}</td>
                      <td className="right">{(row.purchase_count ?? 0).toLocaleString()}</td>
                      <td className="right">{(row.total_revenue ?? 0).toLocaleString()}</td>
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

      {/* ── DQ Rules Table ── */}
      <div className="card" style={{ padding: 0 }}>
        <div className="card-title" style={{ padding: '20px 20px 0 20px' }}>
          <Shield size={16} />
          DQ 규칙 현황
          <span className="card-subtitle">{rules.length}개 규칙</span>
        </div>
        <div style={{ padding: '12px 0 0 0', overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Dimension</th>
                <th>규칙명</th>
                <th>대상</th>
                <th>Layer</th>
                <th className="right">7일 발동</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {rules.length > 0 ? (
                rules.map((rule, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className={`badge ${DIMENSION_BADGE[rule.dimension] ?? 'badge-green'}`}>
                        {rule.dimension}
                      </span>
                    </td>
                    <td className="primary">{rule.rule_name}</td>
                    <td className="mono">{rule.target}</td>
                    <td>
                      <span className={`badge ${LAYER_BADGE[rule.layer] ?? 'badge-blue'}`}>
                        {rule.layer}
                      </span>
                    </td>
                    <td
                      className="right"
                      style={{
                        fontWeight: (rule.trigger_count_7d ?? 0) > 0 ? 600 : 400,
                        color: (rule.trigger_count_7d ?? 0) > 0 ? '#F59E0B' : '#A3A3A3',
                      }}
                    >
                      {rule.trigger_count_7d ?? 0}
                    </td>
                    <td>
                      <span className="badge badge-green">{rule.status}</span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: '#666', padding: 40 }}>
                    데이터 없음
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
