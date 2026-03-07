import { useEffect, useState } from 'react';
import { Activity, TrendingUp, Target, Zap } from 'lucide-react';
import { Tooltip } from '../components/Tooltip';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

// TP/SL Optimize API response
interface OptimizeStrategy {
    take_profit: number;
    stop_loss: number;
    total_pnl: number;
    avg_pnl: number;
    win_rate: number;
    wins: number;
    losses: number;
    profit_factor: number;
}

interface OptimizeData {
    summary: {
        total_signals: number;
        date_range_days: number;
        combinations_tested: number;
    };
    best_by_pnl: OptimizeStrategy[];
    best_by_profit_factor: OptimizeStrategy[];
    all_results: OptimizeStrategy[];
    recommendation: OptimizeStrategy | null;
    error?: string;
}

// Compound API response
interface CompoundData {
    summary: {
        initial_seed: number;
        final_seed: number;
        total_return_pct: number;
        total_trades: number;
    };
    projections: {
        one_week: number;
        one_month: number;
        three_months: number;
        six_months: number;
        one_year: number;
    };
    error?: string;
}

// Time-based API response
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
        highest_win_rate: { time_minutes: number; win_rate: number };
        highest_profit_ratio: { time_minutes: number; profit_ratio: number };
    };
    error?: string;
}

// Profit targets API response
interface ProfitTarget {
    target_pct: number;
    hits: number;
    hit_rate: number;
    avg_time_to_hit: number | null;
}

interface ProfitTargetData {
    summary: { total_signals: number; date_range_days: number };
    targets: ProfitTarget[];
    error?: string;
}

interface TierSummary {
    total: number;
    high: number;
    mid: number;
    small: number;
}

interface PnlTrendEntry {
    label: string;
    trades: number;
    wins: number;
    win_rate: number;
    avg_pnl: number;
}

export default function PerformancePage() {
    const [optimizeData, setOptimizeData] = useState<OptimizeData | null>(null);
    const [compoundData, setCompoundData] = useState<CompoundData | null>(null);
    const [timeBasedData, setTimeBasedData] = useState<TimeBasedData | null>(null);
    const [profitTargetData, setProfitTargetData] = useState<ProfitTargetData | null>(null);
    const [pnlTrendData, setPnlTrendData] = useState<PnlTrendEntry[]>([]);
    const [trendTp, setTrendTp] = useState<number>(0);
    const [trendSl, setTrendSl] = useState<number>(0);
    const [tierSummary, setTierSummary] = useState<TierSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedDays, setSelectedDays] = useState(7);
    const [selectedTier, setSelectedTier] = useState('all');

    const loadPnlTrend = async (tp: number, sl: number, days: number, tier: string) => {
        try {
            const isDaily = days > 0 && days <= 14;
            const endpoint = isDaily ? 'daily-pnl' : 'weekly-pnl';
            const res = await fetch(`/api/system/performance/${endpoint}?take_profit=${tp}&stop_loss=${sl}&days=${days}&tier=${tier}`);
            const json = await res.json();
            setPnlTrendData(isDaily ? (json.days || []) : (json.weeks || []));
        } catch (err) {
            console.error('Failed to load PnL trend:', err);
        }
    };

    const loadAllData = async (days: number, tier: string = selectedTier) => {
        try {
            const [optRes, tbRes, ptRes, tsRes] = await Promise.all([
                fetch(`/api/system/performance/optimize?days=${days}&tier=${tier}`),
                fetch(`/api/system/performance/time-based?days=${days}&tier=${tier}`),
                fetch(`/api/system/performance/profit-targets?days=${days}&tier=${tier}`),
                fetch(`/api/system/performance/tier-summary?days=${days}`)
            ]);

            const optJson = await optRes.json();
            const tbJson = await tbRes.json();
            const ptJson = await ptRes.json();
            const tsJson = await tsRes.json();

            setOptimizeData(optJson);
            setTimeBasedData(tbJson);
            setProfitTargetData(ptJson);
            setTierSummary(tsJson);

            if (optJson.recommendation) {
                const tp = optJson.recommendation.take_profit;
                const sl = optJson.recommendation.stop_loss;
                setTrendTp(tp);
                setTrendSl(sl);

                const [compRes] = await Promise.all([
                    fetch(`/api/system/performance/compound?take_profit=${tp}&stop_loss=${sl}&days=${days}&tier=${tier}`),
                    loadPnlTrend(tp, sl, days, tier)
                ]);
                const compJson = await compRes.json();
                setCompoundData(compJson);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAllData(selectedDays, selectedTier);
        const interval = setInterval(() => loadAllData(selectedDays, selectedTier), 60000);
        return () => clearInterval(interval);
    }, [selectedDays, selectedTier]);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
                <div style={{ color: '#aaa', fontSize: 14 }}>데이터 로딩 중...</div>
            </div>
        );
    }

    // TP/SL levels for heatmap
    const tpLevels = [3, 4, 5, 6, 7, 8, 9, 10];
    const slLevels = [1, 2, 3, 4, 5];

    // Build heatmap data from optimize results
    const heatmapData: Record<string, OptimizeStrategy> = {};
    if (optimizeData?.all_results) {
        optimizeData.all_results.forEach(s => {
            heatmapData[`${s.take_profit}-${s.stop_loss}`] = s;
        });
    }

    // Get min/max avg PnL for color scaling
    const allPnls = Object.values(heatmapData).map(s => s.avg_pnl);
    const maxPnl = Math.max(...allPnls, 0.1);
    const minPnl = Math.min(...allPnls, -0.1);

    const getPnlColor = (pnl: number) => {
        if (pnl >= maxPnl * 0.5) return '#00e676';
        if (pnl >= 0) return '#4caf50';
        if (pnl >= minPnl * 0.5) return '#ff9800';
        return '#f44336';
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Zap size={20} style={{ color: '#82aaff' }} />
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#fff' }}>TP/SL 전략 최적화</h2>
                    <span style={{ fontSize: 12, color: '#888', marginLeft: 4 }}>Rise 알람 기준 매매 전략</span>
                    <Tooltip content="Rise 알람 후 어떤 익절/손절 기준이 최적인지 분석합니다.">
                        <div style={{
                            width: 14, height: 14, borderRadius: '50%', border: '1px solid #666',
                            color: '#666', fontSize: 10, display: 'flex', justifyContent: 'center', alignItems: 'center', cursor: 'help'
                        }}>?</div>
                    </Tooltip>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    {/* Tier filter */}
                    <div style={{ display: 'flex', gap: 4 }}>
                        {([['all', '전체'], ['high', 'High'], ['mid', 'Mid'], ['small', 'Small']] as const).map(([key, label]) => {
                            const tierColors: Record<string, string> = { all: '#82aaff', high: '#ff5252', mid: '#ffd740', small: '#00e676' };
                            const color = tierColors[key];
                            const count = tierSummary ? (key === 'all' ? tierSummary.total : tierSummary[key as 'high' | 'mid' | 'small']) : null;
                            return (
                                <button
                                    key={key}
                                    onClick={() => setSelectedTier(key)}
                                    style={{
                                        padding: '4px 10px',
                                        borderRadius: 6,
                                        border: '1px solid',
                                        borderColor: selectedTier === key ? color : '#333',
                                        background: selectedTier === key ? `${color}18` : 'transparent',
                                        color: selectedTier === key ? color : '#888',
                                        fontSize: 12,
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                    }}
                                >
                                    {label}{count !== null ? ` (${count})` : ''}
                                </button>
                            );
                        })}
                    </div>
                    <div style={{ width: 1, height: 20, background: '#333' }} />
                    {/* Period filter */}
                    <div style={{ display: 'flex', gap: 4 }}>
                        {[7, 14, 30, 0].map(d => (
                            <button
                                key={d}
                                onClick={() => setSelectedDays(d)}
                                style={{
                                    padding: '4px 12px',
                                    borderRadius: 6,
                                    border: '1px solid',
                                    borderColor: selectedDays === d ? '#82aaff' : '#333',
                                    background: selectedDays === d ? 'rgba(130,170,255,0.1)' : 'transparent',
                                    color: selectedDays === d ? '#82aaff' : '#888',
                                    fontSize: 12,
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                }}
                            >
                                {d === 0 ? '전체' : `${d}일`}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Recommendation Hero Card */}
            {optimizeData?.recommendation && (
                <div style={{
                    background: 'linear-gradient(135deg, rgba(130,170,255,0.12) 0%, rgba(130,170,255,0.03) 100%)',
                    border: '1px solid rgba(130,170,255,0.3)',
                    borderRadius: 12,
                    padding: '20px 24px',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                        <Target size={18} style={{ color: '#82aaff' }} />
                        <span style={{ fontSize: 11, color: '#82aaff', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                            추천 전략 ({optimizeData.summary.total_signals}개 신호 기준)
                        </span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 16 }}>
                        <div>
                            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>익절 (TP)</div>
                            <div style={{ fontSize: 28, fontWeight: 800, color: '#00e676' }}>
                                +{optimizeData.recommendation.take_profit}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>손절 (SL)</div>
                            <div style={{ fontSize: 28, fontWeight: 800, color: '#ff5252' }}>
                                -{optimizeData.recommendation.stop_loss}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>승률</div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: optimizeData.recommendation.win_rate >= 50 ? '#00e676' : '#ff5252' }}>
                                {optimizeData.recommendation.win_rate}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>손익비</div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>
                                {optimizeData.recommendation.profit_factor.toFixed(2)}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>평균 PnL</div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: optimizeData.recommendation.avg_pnl >= 0 ? '#00e676' : '#ff5252' }}>
                                {optimizeData.recommendation.avg_pnl >= 0 ? '+' : ''}{optimizeData.recommendation.avg_pnl}%
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* PnL Trend Chart (daily for ≤14d, weekly for 30d/all) */}
            {pnlTrendData.length > 0 && (
                <div style={{
                    background: '#0d1117',
                    borderRadius: 12,
                    border: '1px solid #1c2333',
                    padding: '16px 20px',
                }}>
                    <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <TrendingUp size={16} style={{ color: '#82aaff' }} />
                                <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                                    {selectedDays > 0 && selectedDays <= 14 ? '일별' : '주간별'} 평균 PnL 추이
                                </div>
                            </div>
                            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                                TP/SL 설정 기준 {selectedDays > 0 && selectedDays <= 14 ? '일별' : '주간'} 성과
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ fontSize: 11, color: '#888' }}>TP</span>
                                <select
                                    value={trendTp}
                                    onChange={(e) => { const tp = Number(e.target.value); setTrendTp(tp); loadPnlTrend(tp, trendSl, selectedDays, selectedTier); }}
                                    style={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 4, color: '#00e676', fontSize: 12, padding: '2px 4px', fontWeight: 600 }}
                                >
                                    {[3,4,5,6,7,8,9,10].filter(v => v > trendSl).map(v => <option key={v} value={v}>+{v}%</option>)}
                                </select>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ fontSize: 11, color: '#888' }}>SL</span>
                                <select
                                    value={trendSl}
                                    onChange={(e) => { const sl = Number(e.target.value); setTrendSl(sl); loadPnlTrend(trendTp, sl, selectedDays, selectedTier); }}
                                    style={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 4, color: '#ff5252', fontSize: 12, padding: '2px 4px', fontWeight: 600 }}
                                >
                                    {[1,2,3,4,5].filter(v => v < trendTp).map(v => <option key={v} value={v}>-{v}%</option>)}
                                </select>
                            </div>
                        </div>
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={pnlTrendData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                            <XAxis dataKey="label" stroke="#666" fontSize={10} />
                            <YAxis stroke="#666" fontSize={10} tickFormatter={(v: number) => `${v}%`} />
                            <RechartsTooltip
                                contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                itemStyle={{ color: '#fff' }}
                                labelStyle={{ color: '#fff' }}
                                formatter={(value: number, name: string) => [
                                    `${value >= 0 ? '+' : ''}${value.toFixed(3)}%`,
                                    name === 'avg_pnl' ? '평균 PnL' : name
                                ]}
                                labelFormatter={(label: string) => label}
                            />
                            <ReferenceLine y={0} stroke="#555" strokeDasharray="3 3" />
                            <Bar dataKey="avg_pnl" radius={[4, 4, 0, 0]}>
                                {pnlTrendData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.avg_pnl >= 0 ? '#00e676' : '#ff5252'}
                                        fillOpacity={0.8}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* TP/SL Heatmap + Top 5 + Compound */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px 280px', gap: 16 }}>
                {/* Heatmap */}
                <div style={{
                    background: '#0d1117',
                    borderRadius: 12,
                    border: '1px solid #1c2333',
                    padding: '16px 20px',
                }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <TrendingUp size={16} style={{ color: '#82aaff' }} />
                        TP/SL 조합별 성과
                    </div>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 12 }}>
                        색상: 평균 PnL 기준 (녹색=양수, 빨강=음수)
                    </div>

                    {/* Heatmap Grid */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Header row */}
                        <div style={{ display: 'flex', gap: 2, marginLeft: 40 }}>
                            {slLevels.map(sl => (
                                <div key={sl} style={{ width: 48, textAlign: 'center', fontSize: 10, color: '#888', fontWeight: 600 }}>
                                    SL {sl}%
                                </div>
                            ))}
                        </div>
                        {/* Data rows */}
                        {tpLevels.map(tp => (
                            <div key={tp} style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <div style={{ width: 40, fontSize: 10, color: '#888', fontWeight: 600, textAlign: 'right', paddingRight: 4 }}>
                                    TP {tp}%
                                </div>
                                {slLevels.map(sl => {
                                    const key = `${tp}-${sl}`;
                                    const strategy = heatmapData[key];
                                    const isValid = tp > sl;

                                    if (!isValid) {
                                        return (
                                            <div key={sl} style={{
                                                width: 48, height: 32,
                                                background: '#1a1a1a',
                                                borderRadius: 4,
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                color: '#333',
                                                fontSize: 10
                                            }}>
                                                -
                                            </div>
                                        );
                                    }

                                    if (!strategy) {
                                        return (
                                            <div key={sl} style={{
                                                width: 48, height: 32,
                                                background: '#222',
                                                borderRadius: 4,
                                            }} />
                                        );
                                    }

                                    return (
                                        <Tooltip key={sl} content={`TP ${tp}% / SL ${sl}%: 승률 ${strategy.win_rate}%, 평균 PnL ${strategy.avg_pnl}%`}>
                                            <div style={{
                                                width: 48, height: 32,
                                                background: getPnlColor(strategy.avg_pnl),
                                                borderRadius: 4,
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                cursor: 'pointer',
                                                fontSize: 9,
                                                fontWeight: 600,
                                                color: '#000',
                                            }}>
                                                {strategy.avg_pnl > 0 ? '+' : ''}{strategy.avg_pnl.toFixed(2)}%
                                            </div>
                                        </Tooltip>
                                    );
                                })}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Top 5 Strategies */}
                <div style={{
                    background: '#0d1117',
                    borderRadius: 12,
                    border: '1px solid #1c2333',
                    padding: '16px 20px',
                }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                        Top 5 전략
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4, fontSize: 10, color: '#666', fontWeight: 600, paddingBottom: 4, borderBottom: '1px solid #1c2333' }}>
                            <span>TP</span>
                            <span>SL</span>
                            <span style={{ textAlign: 'right' }}>승률</span>
                            <span style={{ textAlign: 'right' }}>PnL</span>
                        </div>
                        {optimizeData?.best_by_pnl.slice(0, 5).map((s, i) => (
                            <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4, fontSize: 12, alignItems: 'center' }}>
                                <span style={{ color: '#00e676', fontWeight: 600 }}>+{s.take_profit}%</span>
                                <span style={{ color: '#ff5252' }}>-{s.stop_loss}%</span>
                                <span style={{ textAlign: 'right', color: s.win_rate >= 50 ? '#00e676' : '#888' }}>{s.win_rate}%</span>
                                <span style={{ textAlign: 'right', color: s.avg_pnl >= 0 ? '#00e676' : '#ff5252', fontWeight: 600 }}>
                                    {s.avg_pnl >= 0 ? '+' : ''}{s.avg_pnl}%
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Compound Simulation */}
                <div style={{
                    background: '#0d1117',
                    borderRadius: 12,
                    border: '1px solid #1c2333',
                    padding: '16px 20px',
                }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                        복리 수익 시뮬레이션
                    </div>
                    {compoundData?.projections ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>
                                시드 1,000만원 / 포지션 10% 기준
                            </div>
                            {[
                                { label: '7일 후', value: compoundData.projections.one_week },
                                { label: '1달 후', value: compoundData.projections.one_month },
                                { label: '3달 후', value: compoundData.projections.three_months },
                                { label: '6달 후', value: compoundData.projections.six_months },
                                { label: '1년 후', value: compoundData.projections.one_year },
                            ].map(({ label, value }) => {
                                const returnPct = ((value - 1000) / 1000) * 100;
                                return (
                                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                        <span style={{ color: '#888' }}>{label}</span>
                                        <span style={{ color: returnPct >= 0 ? '#00e676' : '#ff5252', fontWeight: 600 }}>
                                            {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(1)}%
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div style={{ color: '#666', fontSize: 12 }}>데이터 없음</div>
                    )}
                </div>
            </div>

            {/* Time-Based Performance Analysis */}
            {timeBasedData && timeBasedData.time_intervals && timeBasedData.time_intervals.length > 0 && (() => {
                const chartDataWithEV = timeBasedData.time_intervals.map(d => ({
                    ...d,
                    expected_value: (d.win_rate / 100) * d.avg_profit - ((100 - d.win_rate) / 100) * d.avg_loss
                }));

                const winRates = chartDataWithEV.map(d => d.win_rate);
                const profitRatios = chartDataWithEV.map(d => d.profit_ratio);
                const evs = chartDataWithEV.map(d => d.expected_value);

                const wrMin = Math.floor(Math.min(...winRates) - 5);
                const wrMax = Math.ceil(Math.max(...winRates) + 5);
                const prMin = Math.floor((Math.min(...profitRatios) - 0.1) * 10) / 10;
                const prMax = Math.ceil((Math.max(...profitRatios) + 0.1) * 10) / 10;
                const evMin = Math.floor((Math.min(...evs) - 0.1) * 10) / 10;
                const evMax = Math.ceil((Math.max(...evs) + 0.1) * 10) / 10;

                const bestEV = chartDataWithEV.reduce((best, curr) =>
                    curr.expected_value > best.expected_value ? curr : best
                );

                return (
                    <div style={{
                        background: '#0d1117',
                        borderRadius: 12,
                        border: '1px solid #1c2333',
                        padding: '16px 20px',
                    }}>
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Activity size={16} style={{ color: '#00e676' }} />
                                <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                                    시간별 성과 분석
                                </div>
                            </div>
                            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                                1분~60분 구간의 승률, 손익비, 기대수익 추이
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
                            <div>
                                <div style={{ fontSize: 12, fontWeight: 600, color: '#00e676', marginBottom: 8 }}>승률 (%)</div>
                                <ResponsiveContainer width="100%" height={160}>
                                    <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                        <XAxis dataKey="time_minutes" stroke="#666" fontSize={9} tickFormatter={(v) => `${v}m`} interval={9} />
                                        <YAxis stroke="#666" fontSize={9} domain={[wrMin, wrMax]} />
                                        <RechartsTooltip
                                            contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                            formatter={(value: number) => [`${value.toFixed(1)}%`, '승률']}
                                            labelFormatter={(label) => `${label}분`}
                                        />
                                        <Line type="monotone" dataKey="win_rate" stroke="#00e676" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            <div>
                                <div style={{ fontSize: 12, fontWeight: 600, color: '#ffd740', marginBottom: 8 }}>손익비</div>
                                <ResponsiveContainer width="100%" height={160}>
                                    <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                        <XAxis dataKey="time_minutes" stroke="#666" fontSize={9} tickFormatter={(v) => `${v}m`} interval={9} />
                                        <YAxis stroke="#666" fontSize={9} domain={[prMin, prMax]} />
                                        <RechartsTooltip
                                            contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                            formatter={(value: number) => [value.toFixed(2), '손익비']}
                                            labelFormatter={(label) => `${label}분`}
                                        />
                                        <ReferenceLine y={1.0} stroke="#555" strokeDasharray="3 3" />
                                        <Line type="monotone" dataKey="profit_ratio" stroke="#ffd740" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            <div>
                                <div style={{ fontSize: 12, fontWeight: 600, color: '#ff6b6b', marginBottom: 8 }}>기대수익 (EV)</div>
                                <ResponsiveContainer width="100%" height={160}>
                                    <LineChart data={chartDataWithEV} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                        <XAxis dataKey="time_minutes" stroke="#666" fontSize={9} tickFormatter={(v) => `${v}m`} interval={9} />
                                        <YAxis stroke="#666" fontSize={9} domain={[evMin, evMax]} />
                                        <RechartsTooltip
                                            contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
                                            formatter={(value: number) => [`${value.toFixed(2)}%`, '기대수익']}
                                            labelFormatter={(label) => `${label}분`}
                                        />
                                        <ReferenceLine y={0} stroke="#555" strokeDasharray="3 3" />
                                        <Line type="monotone" dataKey="expected_value" stroke="#ff6b6b" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

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
                                    최적 매도 시점 (EV 최대)
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>{bestEV.time_minutes}분</div>
                                <div style={{ fontSize: 11, color: '#888' }}>
                                    EV: {bestEV.expected_value.toFixed(2)}%
                                </div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 10, color: '#00e676', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                    최고 승률 시점
                                </div>
                                <div style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>
                                    {timeBasedData.best_intervals.highest_win_rate.time_minutes}분
                                </div>
                                <div style={{ fontSize: 11, color: '#888' }}>
                                    {timeBasedData.best_intervals.highest_win_rate.win_rate}%
                                </div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 10, color: '#ffd740', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                    최고 손익비 시점
                                </div>
                                <div style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>
                                    {timeBasedData.best_intervals.highest_profit_ratio.time_minutes}분
                                </div>
                                <div style={{ fontSize: 11, color: '#888' }}>
                                    {timeBasedData.best_intervals.highest_profit_ratio.profit_ratio.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })()}

            {/* Profit Target Analysis */}
            {profitTargetData && profitTargetData.targets && profitTargetData.targets.length > 0 && (() => {
                const targets = profitTargetData.targets;
                const maxHitRate = Math.max(...targets.map(t => t.hit_rate));

                const validTargets = targets.filter(t => t.target_pct >= 1.0);
                const optimalTarget = validTargets.length > 0
                    ? validTargets.reduce((best, curr) => curr.hit_rate > best.hit_rate ? curr : best)
                    : targets[0];

                return (
                    <div style={{
                        background: '#0d1117',
                        borderRadius: 12,
                        border: '1px solid #1c2333',
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
                                60분 내 각 목표 수익률에 도달한 신호 비율
                            </div>
                        </div>

                        <ResponsiveContainer width="100%" height={180}>
                            <BarChart data={targets} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                                <XAxis dataKey="target_pct" stroke="#666" fontSize={10} tickFormatter={(v) => `${v}%`} />
                                <YAxis stroke="#666" fontSize={10} tickFormatter={(v) => `${v}%`} domain={[0, Math.ceil(maxHitRate / 10) * 10 + 10]} />
                                <RechartsTooltip
                                    contentStyle={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
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
                                    추천 목표 수익률
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>+{optimalTarget.target_pct}%</div>
                                <div style={{ fontSize: 11, color: '#888' }}>
                                    도달 확률 {optimalTarget.hit_rate.toFixed(1)}%
                                    {optimalTarget.avg_time_to_hit && ` | 평균 ${optimalTarget.avg_time_to_hit.toFixed(0)}분`}
                                </div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 10, color: '#666', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                    빠른 참고
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    {[1.0, 2.0, 3.0].map(targetPct => {
                                        const t = targets.find(x => x.target_pct === targetPct);
                                        return t ? (
                                            <div key={targetPct} style={{ fontSize: 11, color: '#888' }}>
                                                +{targetPct}%: <span style={{ color: t.hit_rate >= 50 ? '#00e676' : t.hit_rate >= 30 ? '#ffd740' : '#ff5252', fontWeight: 600 }}>{t.hit_rate.toFixed(1)}%</span>
                                            </div>
                                        ) : null;
                                    })}
                                </div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 10, color: '#666', fontWeight: 600, marginBottom: 4, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                                    고수익 목표
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    {[5.0, 7.0, 10.0].map(targetPct => {
                                        const t = targets.find(x => x.target_pct === targetPct);
                                        return t ? (
                                            <div key={targetPct} style={{ fontSize: 11, color: '#888' }}>
                                                +{targetPct}%: <span style={{ color: t.hit_rate >= 50 ? '#00e676' : t.hit_rate >= 30 ? '#ffd740' : '#ff5252', fontWeight: 600 }}>{t.hit_rate.toFixed(1)}%</span>
                                            </div>
                                        ) : null;
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
}
