import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Shield, AlertTriangle, GitCompareArrows, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { fetchDQOverview, fetchDQScoreTrend, fetchDQReconciliation, fetchDQAnomalies } from '../api/client';

const TIP = {
  contentStyle: { backgroundColor: '#0F0F0F', border: '1px solid #303030', borderRadius: 4, fontSize: 11, fontFamily: "'IBM Plex Mono',monospace", padding: '6px 10px' },
  itemStyle: { color: '#E2E2E2', fontSize: 11, fontFamily: "'IBM Plex Mono',monospace" },
};
const AX = { fill: '#4A4A4A', fontSize: 10, fontFamily: "'IBM Plex Mono',monospace" };

const fmtD = (d: string) => { try { return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }); } catch { return d; } };
const fmtT = (h: string) => { try { return new Date(h).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }); } catch { return h; } };
const fmtDT = (d: string) => { try { const x = new Date(d); return `${x.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })} ${x.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`; } catch { return d; } };
const SEV_B: Record<string, string> = { critical: 'badge-red', warning: 'badge-yellow', info: 'badge-blue' };
const ANOM_L: Record<string, string> = { payment_drop: '결제 급감', category_drop: '카테고리 급감', abnormal_price_spike: '이상 가격', reconciliation_mismatch: '교차검증 불일치' };

function Gauge({ score }: { score: number }) {
  const sz = 44, r = 17, circ = 2 * Math.PI * r, off = circ - (score / 100) * circ;
  const col = score >= 90 ? 'var(--accent)' : score >= 70 ? 'var(--yellow)' : 'var(--red)';
  return (
    <svg width={sz} height={sz} viewBox={`0 0 ${sz} ${sz}`} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx={sz / 2} cy={sz / 2} r={r} className="gauge-bg" />
      <circle cx={sz / 2} cy={sz / 2} r={r} className="gauge-v" stroke={col} strokeDasharray={circ} strokeDashoffset={off} />
    </svg>
  );
}

function Sk({ h = 220 }: { h?: number }) { return <div className="sk" style={{ width: '100%', height: h }} />; }

interface ScoreRow { date: string; completeness_score: number; validity_score: number; timeliness_score: number; total_score: number }
interface ReconRow { hour: string; category_total: number; payment_total: number; diff_pct: number }
interface AnomRow { detected_at: string; anomaly_type: string; dimension: string; expected_value: number | null; actual_value: number | null; severity: string; notes: string | null }
interface DQOv { score: number | null; prev_score: number | null; score_change: number | null; detail: Record<string, number>; anomalies_24h: Record<string, number>; unresolved: number; max_diff_pct: number }

export default function DQPage() {
  const { data: ov, isLoading: ovL } = useQuery<DQOv>({ queryKey: ['dq-overview'], queryFn: fetchDQOverview, refetchInterval: 60_000 });
  const { data: scoreTrend = [], isLoading: stL } = useQuery<ScoreRow[]>({ queryKey: ['dq-score-trend'], queryFn: fetchDQScoreTrend, refetchInterval: 60_000 });
  const { data: recon = [], isLoading: rL } = useQuery<ReconRow[]>({ queryKey: ['dq-recon'], queryFn: fetchDQReconciliation, refetchInterval: 60_000 });
  const { data: anoms = [] } = useQuery<AnomRow[]>({ queryKey: ['dq-anoms'], queryFn: fetchDQAnomalies, refetchInterval: 60_000 });

  const critCnt = ov?.anomalies_24h?.critical ?? 0;
  const warnCnt = ov?.anomalies_24h?.warning ?? 0;

  return (
    <div>
      {/* KPIs */}
      {ovL ? (
        <div className="kpi-row-3">{[0, 1, 2].map(i => <div key={i} className="kpi"><Sk h={56} /></div>)}</div>
      ) : (
        <div className="kpi-row-3">
          <div className={`kpi ${ov?.score != null && ov.score >= 90 ? '' : 'b-red'}`}>
            <div className="kpi-label"><Shield size={13} /> DQ Score</div>
            <div className="kpi-gauge-row">
              {ov?.score != null && <Gauge score={ov.score} />}
              <div>
                <div className={`kpi-value ${ov?.score != null && ov.score >= 90 ? 'green' : 'red'}`}>
                  {ov?.score ?? '--'}
                </div>
                {ov?.score_change != null && (
                  <span className={`trend ${ov.score_change >= 0 ? 'trend-up' : 'trend-down'}`} style={{ fontSize: 11 }}>
                    {ov.score_change >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                    {Math.abs(ov.score_change)} vs 어제
                  </span>
                )}
              </div>
            </div>
            <div className="kpi-sub">
              C:{ov?.detail?.completeness ?? '--'} · V:{ov?.detail?.validity ?? '--'} · T:{ov?.detail?.timeliness ?? '--'}
            </div>
          </div>

          <div className={`kpi ${critCnt > 0 ? 'b-red' : ''}`}>
            <div className="kpi-label"><AlertTriangle size={13} /> Anomalies (24h)</div>
            <div className="kpi-main">
              <span className={`kpi-value ${critCnt > 0 ? 'red' : 'green'}`}>{critCnt + warnCnt}</span>
            </div>
            <div className="kpi-sub">
              {critCnt > 0 && <span className="badge badge-red" style={{ marginRight: 6 }}>{critCnt} critical</span>}
              {warnCnt > 0 && <span className="badge badge-yellow">{warnCnt} warning</span>}
              {critCnt === 0 && warnCnt === 0 && '이상 없음'}
              {ov?.unresolved ? ` · ${ov.unresolved} 미해결` : ''}
            </div>
          </div>

          <div className={`kpi ${(ov?.max_diff_pct ?? 0) > 5 ? 'b-red' : 'b-purple'}`}>
            <div className="kpi-label"><GitCompareArrows size={13} /> Max Reconciliation Diff</div>
            <div className="kpi-main">
              <span className={`kpi-value ${(ov?.max_diff_pct ?? 0) > 5 ? 'red' : ''}`}>{(ov?.max_diff_pct ?? 0).toFixed(1)}%</span>
            </div>
            <div className="kpi-sub">{(ov?.max_diff_pct ?? 0) <= 5 ? '정상 범위 (≤5%)' : '임계치 초과 — 점검 필요'}</div>
          </div>
        </div>
      )}

      {/* Score Trend */}
      <div className="panel">
        <div className="panel-hd"><Shield size={14} /><span className="panel-title">DQ Score Trend</span><span className="panel-meta">14d · C / V / T</span></div>
        <div className="panel-body">
          {stL ? <Sk /> : scoreTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={scoreTrend}>
                <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" />
                <XAxis dataKey="date" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtD} />
                <YAxis domain={[0, 100]} tick={AX} tickLine={false} axisLine={false} />
                <Tooltip {...TIP} labelFormatter={d => { try { return fmtD(d as string); } catch { return String(d); } }} />
                <ReferenceLine y={90} stroke="#EF4444" strokeDasharray="4 4" strokeOpacity={0.4} label={{ value: '90', fill: '#EF4444', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} />
                <Line type="monotone" dataKey="completeness_score" stroke="#3B82F6" strokeWidth={2} name="Completeness" dot={false} />
                <Line type="monotone" dataKey="validity_score" stroke="#22C55E" strokeWidth={2} name="Validity" dot={false} />
                <Line type="monotone" dataKey="timeliness_score" stroke="#F59E0B" strokeWidth={2} name="Timeliness" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="empty">데이터 없음</div>}
        </div>
      </div>

      {/* Recon + Anomalies */}
      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd"><GitCompareArrows size={14} /><span className="panel-title">Reconciliation Diff</span><span className="panel-meta">24h</span></div>
          <div className="panel-body">
            {rL ? <Sk h={200} /> : recon.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={recon}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" />
                  <XAxis dataKey="hour" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtT} />
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip {...TIP} formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(1)}%`, 'diff']} />
                  <ReferenceLine y={5} stroke="#EF4444" strokeDasharray="4 4" strokeOpacity={0.4} label={{ value: '5%', fill: '#EF4444', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} />
                  <Line type="monotone" dataKey="diff_pct" stroke="#A855F7" strokeWidth={2} dot={false} activeDot={{ r: 3, fill: '#A855F7', stroke: '#0E0E0E', strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd"><AlertTriangle size={14} /><span className="panel-title">Recent Anomalies</span><span className="panel-meta">{anoms.length}건</span></div>
          <div className="panel-body flush">
            {anoms.length > 0 ? (
              <div className="tbl-scroll">
                <table className="tbl">
                  <thead><tr><th>시각</th><th>유형</th><th>대상</th><th>심각도</th><th className="r">편차</th></tr></thead>
                  <tbody>
                    {anoms.slice(0, 10).map((a, i) => {
                      const dev = a.expected_value && a.actual_value
                        ? Math.abs((a.actual_value - a.expected_value) / a.expected_value * 100)
                        : null;
                      return (
                        <tr key={i}>
                          <td className="dim" style={{ whiteSpace: 'nowrap' }}>{fmtDT(a.detected_at)}</td>
                          <td className="name">{ANOM_L[a.anomaly_type] ?? a.anomaly_type}</td>
                          <td>{a.dimension}</td>
                          <td><span className={`badge ${SEV_B[a.severity] ?? 'badge-yellow'}`}>{a.severity}</span></td>
                          <td className="r" style={{ color: dev && dev > 50 ? 'var(--red)' : undefined }}>
                            {dev != null ? `${dev.toFixed(0)}%` : '--'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : <div className="empty">이상 탐지 이벤트 없음</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
