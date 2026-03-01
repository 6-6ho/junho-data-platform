import { useEffect, useState } from 'react';
import { fetchSystemPerformance } from '../api/client';
import { BarChart3, Activity, Trophy, Target, TrendingUp } from 'lucide-react';
import { Tooltip } from '../components/Tooltip';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

interface PerformanceSummary {
    window_minutes: number;
    total_signals: number;
    wins: number;
    win_rate: number;
    avg_max_profit: number;
    avg_max_drawdown: number;
    avg_final_profit: number;
    best_profit: number;
    worst_drawdown: number;
}

interface PerformanceResult {
    symbol: string;
    alert_type: string;
    alert_time: string;
    window_minutes: number;
    max_profit_pct: number;
    max_drawdown_pct: number;
    final_profit_pct: number;
    is_win: boolean;
    result_type: string;
}

interface PerformanceData {
    summary: PerformanceSummary[];
    recent: PerformanceResult[];
    error?: string;
}

interface TimeInterval {
    time_minutes: number;
    total_signals: number;
    wins: number;
    losses: number;
    win_rate: number;
    avg_profit: number;
    avg_loss: number;
    profit_ratio: number;
}

interface TimeBasedData {
    summary: {
        total_signals: number;
        date_range_days: number;
    };
    time_intervals: TimeInterval[];
    best_intervals: {
        highest_win_rate: {
            time_minutes: number;
            win_rate: number;
        };
        highest_profit_ratio: {
            time_minutes: number;
            profit_ratio: number;
        };
    };
    error?: string;
}

interface ProfitTarget {
    target_pct: number;
    hits: number;
    hit_rate: number;
    avg_time_to_hit: number | null;
}

interface ProfitTargetData {
    summary: {
        total_signals: number;
        date_range_days: number;
    };
    targets: ProfitTarget[];
    error?: string;
}

const formatPct = (v: number | null | undefined) =>
    v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;

const pctColor = (v: number | null | undefined) =>
    v == null ? '#888' : v >= 0 ? '#00e676' : '#ff5252';

export default function PerformancePage() {
    const [data, setData] = useState<PerformanceData | null>(null);
    const [timeBasedData, setTimeBasedData] = useState<TimeBasedData | null>(null);
    const [profitTargetData, setProfitTargetData] = useState<ProfitTargetData | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedWindow, setSelectedWindow] = useState(60);

    useEffect(() => {
        const loadData = async () => {
            try {
                const res = await fetchSystemPerformance();
                setData(res);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        const loadTimeBasedData = async () => {
            try {
                const res = await fetch('/api/system/performance/time-based?days=7');
                const json = await res.json();
                setTimeBasedData(json);
            } catch (err) {
                console.error('Failed to load time-based data:', err);
            }
        };
        const loadProfitTargetData = async () => {
            try {
                const res = await fetch('/api/system/performance/profit-targets?days=7');
                const json = await res.json();
                setProfitTargetData(json);
            } catch (err) {
                console.error('Failed to load profit target data:', err);
            }
        };
        loadData();
        loadTimeBasedData();
        loadProfitTargetData();
        const interval = setInterval(() => {
            loadData();
            loadTimeBasedData();
            loadProfitTargetData();
        }, 60000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
                <div style={{ color: '#aaa', fontSize: 14 }}>Performance 데이터 로딩 중...</div>
            </div>
        );
    }

    if (!data || data.error) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh', gap: 12 }}>
                <BarChart3 size={32} style={{ color: '#555', opacity: 0.5 }} />
                <div style={{ color: '#888', fontSize: 14 }}>{data?.error || '분석 데이터에 연결할 수 없습니다.'}</div>
            </div>
        );
    }

    const summary = data.summary.find(s => s.window_minutes === selectedWindow) || data.summary[0];
    const otherSummary = data.summary.find(s => s.window_minutes !== selectedWindow);

    // For the bar chart visualization
    const chartData = data.recent.slice().reverse();
    const maxAbsValue = Math.max(
        ...data.recent.map(r => Math.abs(r.max_profit_pct)),
        ...data.recent.map(r => Math.abs(r.max_drawdown_pct)),
        1
    );

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Activity size={20} style={{ color: '#00e676' }} />
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#fff' }}>Performance</h2>
                    <span style={{ fontSize: 12, color: '#888', marginLeft: 4 }}>시그널 성과 분석</span>
                    <div style={{ cursor: 'help', display: 'flex', alignItems: 'center', marginLeft: 4 }}>
                        <Tooltip content="Rise 알림 이후 가격 변동을 추적하여 승률과 수익률을 분석합니다.">
                            <div style={{
                                width: 14, height: 14, borderRadius: '50%', border: '1px solid #666',
                                color: '#666', fontSize: 10, display: 'flex', justifyContent: 'center', alignItems: 'center'
                            }}>?</div>
                        </Tooltip>
                    </div>
                </div>
                {/* Window Toggle */}
                <div style={{ display: 'flex', gap: 4 }}>
                    {data.summary.map(s => (
                        <button
                            key={s.window_minutes}
                            onClick={() => setSelectedWindow(s.window_minutes)}
                            style={{
                                padding: '4px 12px',
                                borderRadius: 6,
                                border: '1px solid',
                                borderColor: selectedWindow === s.window_minutes ? '#00e676' : '#333',
                                background: selectedWindow === s.window_minutes ? 'rgba(0,230,118,0.1)' : 'transparent',
                                color: selectedWindow === s.window_minutes ? '#00e676' : '#888',
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                            }}
                        >
                            {s.window_minutes}m
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Hero Card */}
            {summary && (
                <div style={{
                    background: `linear-gradient(135deg, rgba(0,230,118,0.08) 0%, rgba(0,230,118,0.02) 100%)`,
                    border: '1px solid rgba(0,230,118,0.2)',
                    borderRadius: 12,
                    padding: '20px 24px',
                    display: 'grid',
                    gridTemplateColumns: '1fr auto',
                    gap: 16,
                    alignItems: 'center',
                }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                            <Trophy size={18} style={{ color: '#00e676' }} />
                            <span style={{ fontSize: 11, color: '#00e676', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                                {selectedWindow}분 윈도우 요약
                            </span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                            <div>
                                <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>시그널 수</div>
                                <div style={{ fontSize: 22, fontWeight: 800, color: '#fff' }}>{summary.total_signals}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>승률</div>
                                <div style={{ fontSize: 22, fontWeight: 800, color: summary.win_rate >= 50 ? '#00e676' : '#ff5252' }}>
                                    {summary.win_rate}%
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>평균 최대수익</div>
                                <div style={{ fontSize: 22, fontWeight: 800, color: '#00e676' }}>
                                    +{summary.avg_max_profit}%
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>평균 최대DD</div>
                                <div style={{ fontSize: 22, fontWeight: 800, color: '#ff5252' }}>
                                    {summary.avg_max_drawdown}%
                                </div>
                            </div>
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>W/L 비율</div>
                        <div style={{ fontSize: 28, fontWeight: 800, color: '#fff' }}>
                            {summary.wins}<span style={{ color: '#333', margin: '0 2px' }}>/</span>{summary.total_signals - summary.wins}
                        </div>
                        <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
                            최고: <span style={{ color: '#00e676', fontWeight: 600 }}>+{summary.best_profit}%</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Time-Based Performance Analysis Section */}
            {timeBasedData && timeBasedData.time_intervals && timeBasedData.time_intervals.length > 0 && (() => {
                // 기대 수익 계산: (승률/100) * avg_profit - (1 - 승률/100) * avg_loss
                const chartDataWithEV = timeBasedData.time_intervals.map(d => ({
                    ...d,
                    expected_value: (d.win_rate / 100) * d.avg_profit - ((100 - d.win_rate) / 100) * d.avg_loss
                }));

                // Y축 스케일링을 위한 min/max 계산 (여유 10% 추가)
                const winRates = chartDataWithEV.map(d => d.win_rate);
                const profitRatios = chartDataWithEV.map(d => d.profit_ratio);
                const evs = chartDataWithEV.map(d => d.expected_value);

                const wrMin = Math.floor(Math.min(...winRates) - 5);
                const wrMax = Math.ceil(Math.max(...winRates) + 5);
                const prMin = Math.floor((Math.min(...profitRatios) - 0.1) * 10) / 10;
                const prMax = Math.ceil((Math.max(...profitRatios) + 0.1) * 10) / 10;
                const evMin = Math.floor((Math.min(...evs) - 0.1) * 10) / 10;
                const evMax = Math.ceil((Math.max(...evs) + 0.1) * 10) / 10;

                // 최적 매도 시점 (기대 수익 최대)
                const bestEV = chartDataWithEV.reduce((best, curr) =>
                    curr.expected_value > best.expected_value ? curr : best
                );

                return (
                <div style={{
                    background: '#111',
                    borderRadius: 12,
                    border: '1px solid #222',
                    padding: '16px 20px',
                }}>
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <TrendingUp size={16} style={{ color: '#ffd740' }} />
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                                시간별 성과 분석
                            </div>
                        </div>
                        <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                            5분~240분 구간의 승률, 손익비, 기대수익 추이 ({timeBasedData.summary.total_signals}개 신호 분석)
                        </div>
                    </div>

                    {/* Line Charts - 3개 차트 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
                        {/* Win Rate Chart */}
                        <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#00e676', marginBottom: 8 }}>승률 (%)</div>
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                    <XAxis
                                        dataKey="time_minutes"
                                        stroke="#666"
                                        fontSize={9}
                                        tickFormatter={(value) => `${value}m`}
                                        interval={7}
                                    />
                                    <YAxis stroke="#666" fontSize={9} domain={[wrMin, wrMax]} />
                                    <RechartsTooltip
                                        contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                        labelStyle={{ color: '#fff', fontWeight: 600 }}
                                        formatter={(value: number) => [`${value.toFixed(1)}%`, '승률']}
                                        labelFormatter={(label) => `${label}분 시점`}
                                    />
                                    <Line type="monotone" dataKey="win_rate" stroke="#00e676" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Profit Ratio Chart */}
                        <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#ffd740', marginBottom: 8 }}>손익비 (Ratio)</div>
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                    <XAxis
                                        dataKey="time_minutes"
                                        stroke="#666"
                                        fontSize={9}
                                        tickFormatter={(value) => `${value}m`}
                                        interval={7}
                                    />
                                    <YAxis stroke="#666" fontSize={9} domain={[prMin, prMax]} />
                                    <RechartsTooltip
                                        contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                        labelStyle={{ color: '#fff', fontWeight: 600 }}
                                        formatter={(value: number) => [value.toFixed(2), '손익비']}
                                        labelFormatter={(label) => `${label}분 시점`}
                                    />
                                    <ReferenceLine y={1.0} stroke="#555" strokeDasharray="3 3" />
                                    <Line type="monotone" dataKey="profit_ratio" stroke="#ffd740" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Expected Value Chart (핵심!) */}
                        <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#ff6b6b', marginBottom: 8 }}>기대수익 (EV)</div>
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                    <XAxis
                                        dataKey="time_minutes"
                                        stroke="#666"
                                        fontSize={9}
                                        tickFormatter={(value) => `${value}m`}
                                        interval={7}
                                    />
                                    <YAxis stroke="#666" fontSize={9} domain={[evMin, evMax]} />
                                    <RechartsTooltip
                                        contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                        labelStyle={{ color: '#fff', fontWeight: 600 }}
                                        formatter={(value: number) => [`${value.toFixed(2)}%`, '기대수익']}
                                        labelFormatter={(label) => `${label}분 시점`}
                                    />
                                    <ReferenceLine y={0} stroke="#555" strokeDasharray="3 3" />
                                    <Line type="monotone" dataKey="expected_value" stroke="#ff6b6b" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Optimal Timing Card */}
                    <div style={{
                        background: 'rgba(255,107,107,0.08)',
                        border: '1px solid rgba(255,107,107,0.3)',
                        borderRadius: 8,
                        padding: '12px 16px',
                        display: 'flex',
                        gap: 16,
                    }}>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#ff6b6b', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                🎯 최적 매도 시점 (기대수익 최대)
                            </div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>
                                {bestEV.time_minutes}분
                            </div>
                            <div style={{ fontSize: 11, color: '#888' }}>
                                EV: {bestEV.expected_value.toFixed(2)}% | 승률: {bestEV.win_rate.toFixed(1)}% | 손익비: {bestEV.profit_ratio.toFixed(2)}
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#00e676', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                💡 최고 승률 시점
                            </div>
                            <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>
                                {timeBasedData.best_intervals.highest_win_rate.time_minutes}분
                            </div>
                            <div style={{ fontSize: 11, color: '#888' }}>
                                승률 {timeBasedData.best_intervals.highest_win_rate.win_rate}%
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#ffd740', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                💰 최고 손익비 시점
                            </div>
                            <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>
                                {timeBasedData.best_intervals.highest_profit_ratio.time_minutes}분
                            </div>
                            <div style={{ fontSize: 11, color: '#888' }}>
                                손익비 {timeBasedData.best_intervals.highest_profit_ratio.profit_ratio.toFixed(2)}
                            </div>
                        </div>
                    </div>
                </div>
                );
            })()}

            {/* Profit Target Analysis Section */}
            {profitTargetData && profitTargetData.targets && profitTargetData.targets.length > 0 && (() => {
                const targets = profitTargetData.targets;
                const maxHitRate = Math.max(...targets.map(t => t.hit_rate));

                // Find optimal target (highest hit rate with target >= 1%)
                const validTargets = targets.filter(t => t.target_pct >= 1.0);
                const optimalTarget = validTargets.length > 0
                    ? validTargets.reduce((best, curr) => curr.hit_rate > best.hit_rate ? curr : best)
                    : targets[0];

                return (
                <div style={{
                    background: '#111',
                    borderRadius: 12,
                    border: '1px solid #222',
                    padding: '16px 20px',
                }}>
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Target size={16} style={{ color: '#82aaff' }} />
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                                목표 수익률별 도달 확률
                            </div>
                        </div>
                        <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                            60분 내 각 목표 수익률에 도달한 신호 비율 ({profitTargetData.summary.total_signals}개 신호 분석)
                        </div>
                    </div>

                    {/* Bar Chart for Profit Targets */}
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={targets} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                            <XAxis
                                dataKey="target_pct"
                                stroke="#666"
                                fontSize={10}
                                tickFormatter={(value) => `${value}%`}
                            />
                            <YAxis
                                stroke="#666"
                                fontSize={10}
                                tickFormatter={(value) => `${value}%`}
                                domain={[0, Math.ceil(maxHitRate / 10) * 10 + 10]}
                            />
                            <RechartsTooltip
                                contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                labelStyle={{ color: '#fff', fontWeight: 600 }}
                                formatter={(value: number, name: string, props: any) => {
                                    const target = props.payload;
                                    return [
                                        <span key="content">
                                            도달률: <strong>{value.toFixed(1)}%</strong>
                                            {target.avg_time_to_hit && (
                                                <span style={{ color: '#888' }}> (평균 {target.avg_time_to_hit.toFixed(0)}분)</span>
                                            )}
                                        </span>,
                                        ''
                                    ];
                                }}
                                labelFormatter={(label) => `목표: +${label}%`}
                            />
                            <Bar dataKey="hit_rate" radius={[4, 4, 0, 0]}>
                                {targets.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.hit_rate >= 50 ? '#00e676' : entry.hit_rate >= 30 ? '#ffd740' : '#ff5252'}
                                        fillOpacity={entry.target_pct === optimalTarget.target_pct ? 1 : 0.6}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>

                    {/* Optimal Target Card */}
                    <div style={{
                        background: 'rgba(130,170,255,0.08)',
                        border: '1px solid rgba(130,170,255,0.3)',
                        borderRadius: 8,
                        padding: '12px 16px',
                        marginTop: 16,
                        display: 'flex',
                        gap: 16,
                    }}>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#82aaff', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                🎯 추천 목표 수익률
                            </div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>
                                +{optimalTarget.target_pct}%
                            </div>
                            <div style={{ fontSize: 11, color: '#888' }}>
                                도달 확률 {optimalTarget.hit_rate.toFixed(1)}%
                                {optimalTarget.avg_time_to_hit && ` | 평균 ${optimalTarget.avg_time_to_hit.toFixed(0)}분 소요`}
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#666', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                빠른 참고
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {[1.0, 2.0, 3.0].map(targetPct => {
                                    const t = targets.find(x => x.target_pct === targetPct);
                                    return t ? (
                                        <div key={targetPct} style={{ fontSize: 11, color: '#888' }}>
                                            +{targetPct}%: <span style={{ color: t.hit_rate >= 50 ? '#00e676' : t.hit_rate >= 30 ? '#ffd740' : '#ff5252', fontWeight: 600 }}>{t.hit_rate.toFixed(1)}%</span>
                                            {t.avg_time_to_hit && <span style={{ color: '#555' }}> ({t.avg_time_to_hit.toFixed(0)}분)</span>}
                                        </div>
                                    ) : null;
                                })}
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 10, color: '#666', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                고수익 목표
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {[5.0, 7.0, 10.0].map(targetPct => {
                                    const t = targets.find(x => x.target_pct === targetPct);
                                    return t ? (
                                        <div key={targetPct} style={{ fontSize: 11, color: '#888' }}>
                                            +{targetPct}%: <span style={{ color: t.hit_rate >= 50 ? '#00e676' : t.hit_rate >= 30 ? '#ffd740' : '#ff5252', fontWeight: 600 }}>{t.hit_rate.toFixed(1)}%</span>
                                            {t.avg_time_to_hit && <span style={{ color: '#555' }}> ({t.avg_time_to_hit.toFixed(0)}분)</span>}
                                        </div>
                                    ) : null;
                                })}
                            </div>
                        </div>
                    </div>
                </div>
                );
            })()}

            {/* Profit Distribution (CSS Bars) + Insights Side Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>

                {/* Bar Chart */}
                <div style={{
                    background: '#111',
                    borderRadius: 12,
                    border: '1px solid #222',
                    padding: '16px 20px',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>시그널 수익 분포</div>
                            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>최근 {chartData.length}개 시그널의 최대 수익률</div>
                        </div>
                        <div style={{ display: 'flex', gap: 12 }}>
                            <span style={{ fontSize: 10, color: '#00e676', display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ width: 8, height: 8, borderRadius: 2, background: '#00e676', display: 'inline-block' }} />WIN
                            </span>
                            <span style={{ fontSize: 10, color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ width: 8, height: 8, borderRadius: 2, background: '#333', display: 'inline-block' }} />OTHER
                            </span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 180 }}>
                        {chartData.map((r, i) => {
                            const height = Math.max((Math.abs(r.max_profit_pct) / maxAbsValue) * 160, 2);
                            const isPositive = r.max_profit_pct >= 0;
                            return (
                                <div
                                    key={i}
                                    title={`${r.symbol}: ${formatPct(r.max_profit_pct)}`}
                                    style={{
                                        flex: 1,
                                        height,
                                        borderRadius: '3px 3px 0 0',
                                        background: r.is_win
                                            ? 'linear-gradient(to top, rgba(0,230,118,0.3), rgba(0,230,118,0.7))'
                                            : isPositive
                                                ? 'linear-gradient(to top, rgba(100,100,100,0.2), rgba(100,100,100,0.5))'
                                                : 'linear-gradient(to top, rgba(255,82,82,0.3), rgba(255,82,82,0.5))',
                                        cursor: 'default',
                                        transition: 'opacity 0.15s',
                                        minWidth: 4,
                                    }}
                                    onMouseEnter={(e) => { (e.target as HTMLElement).style.opacity = '0.7'; }}
                                    onMouseLeave={(e) => { (e.target as HTMLElement).style.opacity = '1'; }}
                                />
                            );
                        })}
                    </div>
                    {/* X-axis labels (symbol names, sparse) */}
                    <div style={{ display: 'flex', gap: 2, marginTop: 4 }}>
                        {chartData.map((r, i) => (
                            <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: 8, color: '#555', overflow: 'hidden' }}>
                                {i % Math.ceil(chartData.length / 8) === 0 ? r.symbol.replace('USDT', '') : ''}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Insights Panel */}
                <div style={{
                    background: '#111',
                    borderRadius: 12,
                    border: '1px solid #222',
                    padding: '16px 20px',
                    display: 'flex',
                    flexDirection: 'column',
                }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Target size={16} style={{ color: '#ffd740' }} />
                        인사이트
                    </div>

                    {summary && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1 }}>
                            <InsightRow label="Win/Loss 비율" value={`${summary.wins} / ${summary.total_signals - summary.wins}`} />
                            <InsightRow
                                label="Risk/Reward"
                                value={`1 : ${Math.abs(summary.avg_max_profit / (summary.avg_max_drawdown || 1)).toFixed(2)}`}
                                color="#00e676"
                            />
                            <InsightRow
                                label="기대 수익률"
                                value={formatPct(summary.avg_final_profit)}
                                color={summary.avg_final_profit >= 0 ? '#00e676' : '#ff5252'}
                            />
                            <InsightRow
                                label="최악의 DD"
                                value={formatPct(summary.worst_drawdown)}
                                color="#ff5252"
                            />

                            {otherSummary && (
                                <>
                                    <div style={{ borderTop: '1px solid #222', marginTop: 4, paddingTop: 12 }}>
                                        <div style={{ fontSize: 10, color: '#666', fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', marginBottom: 8 }}>
                                            {otherSummary.window_minutes}분 윈도우 비교
                                        </div>
                                        <InsightRow label="승률" value={`${otherSummary.win_rate}%`} color={otherSummary.win_rate >= 50 ? '#00e676' : '#ff5252'} />
                                        <InsightRow label="평균 최대수익" value={`+${otherSummary.avg_max_profit}%`} color="#00e676" />
                                    </div>
                                </>
                            )}

                            <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid #222' }}>
                                <div style={{
                                    background: '#0a0a0a',
                                    borderRadius: 8,
                                    padding: '10px 12px',
                                    fontSize: 11,
                                    color: '#666',
                                    lineHeight: 1.5,
                                    border: '1px solid #1a1a1a',
                                }}>
                                    <div style={{ color: '#ffd740', fontWeight: 600, fontSize: 10, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                        분석 기준
                                    </div>
                                    5분봉 기준 3%↑ 급등 감지 후 {selectedWindow}분간 가격 추적.
                                    WIN = 최대수익 {'>'} 1%
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Recent Signal Logs Table */}
            <div style={{
                background: '#111',
                borderRadius: 12,
                border: '1px solid #222',
                overflow: 'hidden',
            }}>
                {/* Table Header Bar */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 16px',
                    borderBottom: '1px solid #222',
                }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>시그널 로그</div>
                    <span style={{ fontSize: 11, color: '#666' }}>최근 20건</span>
                </div>

                {/* Column Headers */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '100px 1fr 80px 90px 90px 90px 70px',
                    padding: '8px 16px',
                    background: '#0a0a0a',
                    borderBottom: '1px solid #222',
                    fontSize: 11,
                    color: '#666',
                    fontWeight: 600,
                    letterSpacing: 0.5,
                }}>
                    <span>시간</span>
                    <span>심볼</span>
                    <span>타입</span>
                    <span style={{ textAlign: 'right' }}>최대수익</span>
                    <span style={{ textAlign: 'right' }}>최대DD</span>
                    <span style={{ textAlign: 'right' }}>최종({selectedWindow}m)</span>
                    <span style={{ textAlign: 'center' }}>결과</span>
                </div>

                {/* Rows */}
                {data.recent.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#666', fontSize: 13 }}>
                        <BarChart3 size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
                        <div>시그널 로그가 없습니다.</div>
                    </div>
                ) : (
                    data.recent.map((row, i) => (
                        <div
                            key={i}
                            style={{
                                display: 'grid',
                                gridTemplateColumns: '100px 1fr 80px 90px 90px 90px 70px',
                                padding: '10px 16px',
                                borderBottom: '1px solid #1a1a1a',
                                alignItems: 'center',
                                transition: 'background 0.15s',
                                cursor: 'default',
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                        >
                            <span style={{ fontSize: 12, color: '#888', fontFamily: 'monospace' }}>
                                {row.alert_time ? new Date(row.alert_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : '—'}
                            </span>
                            <span style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>
                                {row.symbol.replace('USDT', '')}
                                <span style={{ color: '#555', fontWeight: 400 }}>/USDT</span>
                            </span>
                            <span style={{
                                fontSize: 10,
                                color: '#888',
                                background: '#1a1a1a',
                                padding: '2px 6px',
                                borderRadius: 4,
                                border: '1px solid #222',
                                textTransform: 'uppercase',
                                fontWeight: 600,
                                letterSpacing: 0.5,
                                width: 'fit-content',
                            }}>
                                {row.alert_type}
                            </span>
                            <span style={{
                                textAlign: 'right',
                                fontSize: 13,
                                fontWeight: 700,
                                color: '#00e676',
                            }}>
                                +{row.max_profit_pct.toFixed(2)}%
                            </span>
                            <span style={{
                                textAlign: 'right',
                                fontSize: 12,
                                color: '#ff5252',
                                opacity: 0.7,
                            }}>
                                {row.max_drawdown_pct.toFixed(2)}%
                            </span>
                            <span style={{
                                textAlign: 'right',
                                fontSize: 13,
                                fontWeight: 600,
                                color: pctColor(row.final_profit_pct),
                            }}>
                                {formatPct(row.final_profit_pct)}
                            </span>
                            <span style={{ textAlign: 'center' }}>
                                <span style={{
                                    fontSize: 10,
                                    fontWeight: 700,
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                    letterSpacing: 0.5,
                                    border: '1px solid',
                                    ...(row.is_win
                                        ? { color: '#00e676', borderColor: 'rgba(0,230,118,0.2)', background: 'rgba(0,230,118,0.08)' }
                                        : row.result_type === 'LOSS'
                                            ? { color: '#ff5252', borderColor: 'rgba(255,82,82,0.2)', background: 'rgba(255,82,82,0.08)' }
                                            : { color: '#888', borderColor: '#333', background: 'rgba(100,100,100,0.08)' }),
                                }}>
                                    {row.result_type}
                                </span>
                            </span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

function InsightRow({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '6px 0',
        }}>
            <span style={{ fontSize: 12, color: '#888' }}>{label}</span>
            <span style={{ fontSize: 14, fontWeight: 700, color: color || '#fff', fontFamily: 'monospace' }}>{value}</span>
        </div>
    );
}
