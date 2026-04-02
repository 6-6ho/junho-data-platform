import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { Shield, AlertTriangle, GitCompareArrows, ArrowUpRight, ArrowDownRight } from 'lucide-react';

const API = '/api/dq';
const TIP = {
  contentStyle: { background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 6, fontSize: 12 },
  itemStyle: { color: 'var(--text-primary)', fontSize: 12 },
};
const AX = { fill: 'var(--text-tertiary)', fontSize: 10 };
const fmtD = (d: string) => { try { return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }); } catch { return d; } };
const fmtT = (h: string) => { try { return new Date(h).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }); } catch { return h; } };
const fmtDT = (d: string) => { try { const x = new Date(d); return `${x.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })} ${x.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`; } catch { return d; } };
interface DQOverview { score: number | null; prev_score: number | null; score_change: number | null; detail: Record<string, number>; anomalies_24h: Record<string, number>; unresolved: number; max_diff_pct: number }
interface ScoreRow { date: string; completeness: number; validity: number; timeliness: number; total: number }
interface ReconRow { hour: string; source_count: number; symbol_count: number; diff_pct: number }
interface AnomRow { detected_at: string; anomaly_type: string; dimension: string; expected_value: number | null; actual_value: number | null; severity: string; notes: string | null }

const ANOM_L: Record<string, string> = { symbol_drop: '심볼 드롭', price_outlier: '가격 이상', recon_mismatch: '교차검증 불일치' };
const SEV_CL: Record<string, string> = { critical: 'var(--red)', warning: '#F59E0B' };

function Gauge({ score }: { score: number }) {
  const r = 17, circ = 2 * Math.PI * r, off = circ - (score / 100) * circ;
  const col = score >= 90 ? 'var(--green)' : score >= 70 ? '#F59E0B' : 'var(--red)';
  return (
    <svg width={44} height={44} viewBox="0 0 44 44" style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={22} cy={22} r={r} fill="none" stroke="var(--border-color)" strokeWidth={4} />
      <circle cx={22} cy={22} r={r} fill="none" stroke={col} strokeWidth={4} strokeDasharray={circ} strokeDashoffset={off} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
    </svg>
  );
}

export default function DQPage() {
  const { data: ov } = useQuery<DQOverview>({ queryKey: ['dq-overview'], queryFn: () => fetch(`${API}/overview`).then(r => r.json()), refetchInterval: 60_000 });
  const { data: trend = [] } = useQuery<ScoreRow[]>({ queryKey: ['dq-trend'], queryFn: () => fetch(`${API}/score-trend`).then(r => r.json()), refetchInterval: 60_000 });
  const { data: recon = [] } = useQuery<ReconRow[]>({ queryKey: ['dq-recon'], queryFn: () => fetch(`${API}/reconciliation`).then(r => r.json()), refetchInterval: 60_000 });
  const { data: anoms = [] } = useQuery<AnomRow[]>({ queryKey: ['dq-anoms'], queryFn: () => fetch(`${API}/anomalies`).then(r => r.json()), refetchInterval: 60_000 });

  const critCnt = ov?.anomalies_24h?.critical ?? 0;
  const warnCnt = ov?.anomalies_24h?.warning ?? 0;

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Data Quality</h2>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Shield size={13} /> DQ Score
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {ov?.score != null && <Gauge score={ov.score} />}
            <div>
              <div style={{ fontSize: 28, fontWeight: 700, color: ov?.score != null && ov.score >= 90 ? 'var(--green)' : 'var(--red)' }}>
                {ov?.score ?? '--'}
              </div>
              {ov?.score_change != null && (
                <span style={{ fontSize: 12, fontWeight: 600, color: ov.score_change >= 0 ? 'var(--green)' : 'var(--red)', display: 'flex', alignItems: 'center', gap: 2 }}>
                  {ov.score_change >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                  {Math.abs(ov.score_change)} vs 어제
                </span>
              )}
            </div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 6 }}>
            C:{ov?.detail?.completeness ?? '--'} · V:{ov?.detail?.validity ?? '--'} · T:{ov?.detail?.timeliness ?? '--'}
          </div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={13} /> Anomalies (24h)
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: critCnt > 0 ? 'var(--red)' : 'var(--green)' }}>
            {critCnt + warnCnt}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 6, display: 'flex', gap: 8 }}>
            {critCnt > 0 && <span style={{ color: 'var(--red)' }}>{critCnt} critical</span>}
            {warnCnt > 0 && <span style={{ color: '#F59E0B' }}>{warnCnt} warning</span>}
            {critCnt === 0 && warnCnt === 0 && '이상 없음'}
          </div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <GitCompareArrows size={13} /> Reconciliation Diff
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: (ov?.max_diff_pct ?? 0) > 5 ? 'var(--red)' : 'var(--text-primary)' }}>
            {(ov?.max_diff_pct ?? 0).toFixed(1)}%
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 6 }}>
            {(ov?.max_diff_pct ?? 0) <= 5 ? '정상 범위 (≤5%)' : '임계치 초과'}
          </div>
        </div>
      </div>

      {/* Score Trend */}
      {trend.length > 0 && (
        <div className="card" style={{ padding: 16, marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Shield size={14} style={{ color: 'var(--green)' }} /> DQ Score Trend
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-tertiary)' }}>14d · C / V / T</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="date" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtD} />
              <YAxis domain={[0, 100]} tick={AX} tickLine={false} axisLine={false} />
              <Tooltip {...TIP} />
              <ReferenceLine y={90} stroke="var(--red)" strokeDasharray="4 4" strokeOpacity={0.4} />
              <Line type="monotone" dataKey="completeness" stroke="#3B82F6" strokeWidth={2} name="Completeness" dot={false} />
              <Line type="monotone" dataKey="validity" stroke="#22C55E" strokeWidth={2} name="Validity" dot={false} />
              <Line type="monotone" dataKey="timeliness" stroke="#F59E0B" strokeWidth={2} name="Timeliness" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Reconciliation + Anomalies */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <GitCompareArrows size={14} style={{ color: 'var(--green)' }} /> Reconciliation
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-tertiary)' }}>24h</span>
          </div>
          {recon.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={recon}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="hour" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtT} />
                <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} />
                <Tooltip {...TIP} formatter={(v) => [`${Number(v ?? 0).toFixed(1)}%`, 'diff']} />
                <ReferenceLine y={5} stroke="var(--red)" strokeDasharray="4 4" strokeOpacity={0.4} />
                <Line type="monotone" dataKey="diff_pct" stroke="#A855F7" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-tertiary)', fontSize: 12 }}>데이터 없음</div>}
        </div>

        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, borderBottom: '1px solid var(--border-color)' }}>
            <AlertTriangle size={14} style={{ color: 'var(--green)' }} /> Recent Anomalies
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-tertiary)' }}>{anoms.length}건</span>
          </div>
          {anoms.length > 0 ? (
            <div style={{ maxHeight: 220, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '6px 12px', textAlign: 'left', fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>시각</th>
                    <th style={{ padding: '6px 12px', textAlign: 'left', fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>유형</th>
                    <th style={{ padding: '6px 12px', textAlign: 'left', fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>심각도</th>
                    <th style={{ padding: '6px 12px', textAlign: 'right', fontSize: 10, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>편차</th>
                  </tr>
                </thead>
                <tbody>
                  {anoms.slice(0, 10).map((a, i) => {
                    const dev = a.expected_value && a.actual_value ? Math.abs((a.actual_value - a.expected_value) / a.expected_value * 100) : null;
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '6px 12px', color: 'var(--text-tertiary)', fontSize: 11, whiteSpace: 'nowrap' }}>{fmtDT(a.detected_at)}</td>
                        <td style={{ padding: '6px 12px', color: 'var(--text-primary)' }}>{ANOM_L[a.anomaly_type] ?? a.anomaly_type}</td>
                        <td style={{ padding: '6px 12px' }}>
                          <span style={{ fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 3, color: SEV_CL[a.severity] ?? '#F59E0B', background: `${SEV_CL[a.severity] ?? '#F59E0B'}15` }}>{a.severity}</span>
                        </td>
                        <td style={{ padding: '6px 12px', textAlign: 'right', color: dev && dev > 50 ? 'var(--red)' : 'var(--text-secondary)' }}>{dev != null ? `${dev.toFixed(0)}%` : '--'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-tertiary)', fontSize: 12 }}>이상 없음</div>}
        </div>
      </div>
    </div>
  );
}
