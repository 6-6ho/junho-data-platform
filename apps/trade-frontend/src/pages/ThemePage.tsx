import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Flame, BarChart3, Layers, Zap } from 'lucide-react';
import { Tooltip } from '../components/Tooltip';

const API_BASE = '/api/theme';

// --- Static Theme Types ---
interface ThemeRS {
    theme_id: number;
    theme_name: string;
    coin_count: number;
    avg_change_pct: number;
    market_avg_pct: number;
    rs_score: number;
    top_coin: string;
    top_coin_name: string;
    best_pct: number;
    exclude_from_rs: boolean;
}

interface ThemeCoin {
    symbol: string;
    name_kr: string;
    listed_period: string;
    note: string;
    change_pct_24h: number | null;
    change_pct_window: number | null;
    vol_ratio: number | null;
    event_time: string | null;
}

// --- Dynamic Theme Types (v2: correlation-based) ---
interface DynamicCluster {
    cluster_id: number;
    created_date: string;
    coin_count: number;
    strength_score: number;
    avg_high_change_pct: number;
    lead_symbol: string | null;
    lead_change_pct: number | null;
    avg_correlation: number | null;
}

interface DynamicMember {
    symbol: string;
    daily_change_pct: number | null;
    correlation_to_lead: number | null;
    change_pct_24h: number | null;
    vol_ratio: number | null;
}

type TabType = 'static' | 'dynamic';

const formatPct = (v: number | null) => v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const pctColor = (v: number | null) => v == null ? '#888' : v >= 0 ? '#00e676' : '#ff5252';
// ==================== Static Theme Tab ====================
function StaticThemeTab() {
    const [themes, setThemes] = useState<ThemeRS[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [coins, setCoins] = useState<ThemeCoin[]>([]);
    const [coinsLoading, setCoinsLoading] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<string>('');

    const fetchRS = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/rs`);
            const data = await res.json();
            setThemes(data.themes || []);
            if (data.timestamp) {
                setLastUpdate(new Date(data.timestamp).toLocaleTimeString('ko-KR'));
            } else {
                setLastUpdate(new Date().toLocaleTimeString('ko-KR'));
            }
        } catch (e) {
            console.error('Failed to fetch theme RS:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchRS();
        const interval = setInterval(fetchRS, 30000);
        return () => clearInterval(interval);
    }, [fetchRS]);

    const toggleExpand = async (themeId: number) => {
        if (expandedId === themeId) {
            setExpandedId(null);
            setCoins([]);
            return;
        }
        setExpandedId(themeId);
        setCoinsLoading(true);
        try {
            const res = await fetch(`${API_BASE}/${themeId}/coins`);
            const data = await res.json();
            setCoins(data.coins || []);
        } catch (e) {
            console.error('Failed to fetch coins:', e);
        } finally {
            setCoinsLoading(false);
        }
    };

    const topTheme = themes[0];

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '40vh' }}>
                <div style={{ color: '#aaa', fontSize: 14 }}>테마 데이터 로딩 중...</div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Layers size={20} style={{ color: '#82aaff' }} />
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>테마 RS</span>
                    <div style={{ cursor: 'help', display: 'flex', alignItems: 'center' }}>
                        <Tooltip content="사전 정의된 테마(밈코인, AI, 레이어1 등) 기반으로 상대강도(RS)를 계산합니다. 10분마다 갱신.">
                            <div style={{
                                width: 14, height: 14, borderRadius: '50%', border: '1px solid #666',
                                color: '#666', fontSize: 10, display: 'flex', justifyContent: 'center', alignItems: 'center'
                            }}>?</div>
                        </Tooltip>
                    </div>
                </div>
                <span style={{ fontSize: 11, color: '#666' }}>
                    Updated {lastUpdate}
                </span>
            </div>

            {/* Today's Top Theme */}
            {topTheme && (
                <div style={{
                    background: 'linear-gradient(135deg, rgba(130,170,255,0.08) 0%, rgba(130,170,255,0.02) 100%)',
                    border: '1px solid rgba(130,170,255,0.2)',
                    borderRadius: 12,
                    padding: '20px 24px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                            <Flame size={18} style={{ color: '#82aaff' }} />
                            <span style={{ fontSize: 11, color: '#82aaff', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>오늘의 테마</span>
                        </div>
                        <div style={{ fontSize: 24, fontWeight: 800, color: '#fff', marginBottom: 4 }}>
                            {topTheme.theme_name}
                        </div>
                        <div style={{ fontSize: 12, color: '#aaa' }}>
                            {topTheme.coin_count}개 코인 · 1위: {topTheme.top_coin_name || topTheme.top_coin} ({formatPct(topTheme.best_pct)})
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 32, fontWeight: 800, color: pctColor(topTheme.avg_change_pct) }}>
                            {formatPct(topTheme.avg_change_pct)}
                        </div>
                        <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                            RS {topTheme.rs_score?.toFixed(2) || '—'} · 시장 {formatPct(topTheme.market_avg_pct)}
                        </div>
                    </div>
                </div>
            )}

            {/* Theme RS Table */}
            <div style={{
                background: '#0d1117',
                borderRadius: 12,
                border: '1px solid #1c2333',
                overflow: 'hidden',
            }}>
                {/* Table Header */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '40px 1fr 80px 100px 80px 60px 40px',
                    padding: '10px 16px',
                    background: '#0a0a0a',
                    borderBottom: '1px solid #222',
                    fontSize: 11,
                    color: '#666',
                    fontWeight: 600,
                    letterSpacing: 0.5,
                }}>
                    <span>#</span>
                    <span>테마</span>
                    <span style={{ textAlign: 'right' }}>RS</span>
                    <span style={{ textAlign: 'right' }}>평균 변동</span>
                    <span style={{ textAlign: 'right' }}>Top 코인</span>
                    <span style={{ textAlign: 'right' }}>코인수</span>
                    <span />
                </div>

                {/* Theme Rows */}
                {themes.map((t, idx) => (
                    <div key={t.theme_id}>
                        <div
                            onClick={() => toggleExpand(t.theme_id)}
                            style={{
                                display: 'grid',
                                gridTemplateColumns: '40px 1fr 80px 100px 80px 60px 40px',
                                padding: '12px 16px',
                                borderBottom: '1px solid #1a1a1a',
                                cursor: 'pointer',
                                transition: 'background 0.15s',
                                background: expandedId === t.theme_id ? 'rgba(130,170,255,0.04)' : 'transparent',
                                alignItems: 'center',
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = expandedId === t.theme_id ? 'rgba(130,170,255,0.04)' : 'transparent'; }}
                        >
                            <span style={{ fontSize: 13, fontWeight: 700, color: idx < 3 ? '#82aaff' : '#666' }}>
                                {idx + 1}
                            </span>
                            <div>
                                <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{t.theme_name}</span>
                            </div>
                            <span style={{
                                textAlign: 'right',
                                fontSize: 13,
                                fontWeight: 700,
                                color: t.rs_score > 1 ? '#00e676' : t.rs_score < -1 ? '#ff5252' : '#888',
                            }}>
                                {t.rs_score?.toFixed(2) || '—'}
                            </span>
                            <span style={{
                                textAlign: 'right',
                                fontSize: 13,
                                fontWeight: 600,
                                color: pctColor(t.avg_change_pct),
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'flex-end',
                                gap: 4,
                            }}>
                                {t.avg_change_pct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                                {formatPct(t.avg_change_pct)}
                            </span>
                            <span style={{ textAlign: 'right', fontSize: 12, color: '#aaa' }}>
                                {t.top_coin}
                            </span>
                            <span style={{ textAlign: 'right', fontSize: 12, color: '#666' }}>
                                {t.coin_count}
                            </span>
                            <span style={{ textAlign: 'right', color: '#666' }}>
                                {expandedId === t.theme_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </span>
                        </div>

                        {/* Expanded Coins Panel */}
                        {expandedId === t.theme_id && (
                            <div style={{
                                background: 'rgba(130,170,255,0.02)',
                                borderBottom: '1px solid #222',
                                padding: '8px 16px 12px 56px',
                            }}>
                                {coinsLoading ? (
                                    <div style={{ color: '#666', fontSize: 12, padding: 8 }}>로딩 중...</div>
                                ) : (
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                                        {coins.map((c) => (
                                            <div key={c.symbol} style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                padding: '8px 12px',
                                                background: '#0d0d0d',
                                                borderRadius: 8,
                                                border: '1px solid #1a1a1a',
                                            }}>
                                                <div>
                                                    <span style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{c.symbol}</span>
                                                    <span style={{ fontSize: 11, color: '#666', marginLeft: 6 }}>{c.name_kr}</span>
                                                </div>
                                                <span style={{ fontSize: 13, fontWeight: 600, color: pctColor(c.change_pct_24h) }}>
                                                    {formatPct(c.change_pct_24h)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {themes.length === 0 && (
                    <div style={{ padding: 40, textAlign: 'center', color: '#666', fontSize: 13 }}>
                        <BarChart3 size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
                        <div>movers 데이터가 없어 RS를 계산할 수 없습니다.</div>
                        <div style={{ fontSize: 11, marginTop: 4 }}>Trade 서비스가 활성화되면 자동으로 데이터가 수집됩니다.</div>
                    </div>
                )}
            </div>
        </div>
    );
}

// ==================== Dynamic Theme Tab (v2: correlation-based) ====================
function DynamicThemeTab() {
    const [clusters, setClusters] = useState<DynamicCluster[]>([]);
    const [loading, setLoading] = useState(true);
    const [dynamicDate, setDynamicDate] = useState<string>('');
    const [expandedClusterId, setExpandedClusterId] = useState<number | null>(null);
    const [clusterMembers, setClusterMembers] = useState<DynamicMember[]>([]);
    const [membersLoading, setMembersLoading] = useState(false);

    const fetchDynamic = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/dynamic`);
            const data = await res.json();
            setClusters(data.clusters || []);
            setDynamicDate(data.date || '');
        } catch (e) {
            console.error('Failed to fetch dynamic themes:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDynamic();
    }, [fetchDynamic]);

    const toggleClusterExpand = async (clusterId: number) => {
        if (expandedClusterId === clusterId) {
            setExpandedClusterId(null);
            setClusterMembers([]);
            return;
        }
        setExpandedClusterId(clusterId);
        setMembersLoading(true);
        try {
            const res = await fetch(`${API_BASE}/dynamic/${clusterId}`);
            const data = await res.json();
            setClusterMembers(data.members || []);
        } catch (e) {
            console.error('Failed to fetch cluster members:', e);
        } finally {
            setMembersLoading(false);
        }
    };

    const formatCorr = (v: number | null) => v == null ? '—' : v.toFixed(2);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '40vh' }}>
                <div style={{ color: '#aaa', fontSize: 14 }}>동적 테마 로딩 중...</div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Zap size={20} style={{ color: '#82aaff' }} />
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>동적 테마</span>
                    <div style={{ cursor: 'help', display: 'flex', alignItems: 'center' }}>
                        <Tooltip content="14일간 시장 중립(BTC 수익률 차감) 5분봉 상관관계 기반. BTC 효과를 제거하고 진짜 같이 움직이는 코인만 클러스터링(계층적 군집화, 상관 0.65+).">
                            <div style={{
                                width: 14, height: 14, borderRadius: '50%', border: '1px solid #666',
                                color: '#666', fontSize: 10, display: 'flex', justifyContent: 'center', alignItems: 'center'
                            }}>?</div>
                        </Tooltip>
                    </div>
                </div>
                <span style={{ fontSize: 11, color: '#666' }}>
                    {dynamicDate ? `Date: ${dynamicDate}` : ''}
                </span>
            </div>

            {/* Today's TOP card — first cluster by strength */}
            {clusters.length > 0 && (() => {
                const top = clusters[0];
                return (
                    <div style={{
                        background: 'linear-gradient(135deg, rgba(130,170,255,0.08) 0%, rgba(130,170,255,0.02) 100%)',
                        border: '1px solid rgba(130,170,255,0.2)',
                        borderRadius: 12,
                        padding: '20px 24px',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                            <Flame size={18} style={{ color: '#82aaff' }} />
                            <span style={{ fontSize: 11, color: '#82aaff', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                                오늘의 TOP 클러스터
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontSize: 24, fontWeight: 800, color: '#fff', marginBottom: 4 }}>
                                    {top.lead_symbol?.replace('USDT', '') || '—'}
                                </div>
                                <div style={{ fontSize: 12, color: '#aaa' }}>
                                    {top.coin_count}개 코인 · 평균 상관 {formatCorr(top.avg_correlation)}
                                </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: 32, fontWeight: 800, color: pctColor(top.lead_change_pct) }}>
                                    {formatPct(top.lead_change_pct)}
                                </div>
                                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                                    강도 {top.strength_score.toFixed(1)}
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })()}

            {clusters.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#666', fontSize: 13 }}>
                    <Zap size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
                    <div>동적 테마 데이터가 없습니다.</div>
                    <div style={{ fontSize: 11, marginTop: 4 }}>매일 KST 06:00에 전날 데이터 기반으로 자동 생성됩니다.</div>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {clusters.map((c, idx) => (
                        <div key={c.cluster_id} style={{
                            background: '#0d1117',
                            borderRadius: 12,
                            border: expandedClusterId === c.cluster_id
                                ? '1px solid rgba(130,170,255,0.3)'
                                : '1px solid #1c2333',
                            overflow: 'hidden',
                            transition: 'border-color 0.15s',
                        }}>
                            {/* Cluster Card */}
                            <div
                                onClick={() => toggleClusterExpand(c.cluster_id)}
                                style={{
                                    padding: '16px 20px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                    <div style={{
                                        width: 32, height: 32, borderRadius: 8,
                                        background: `rgba(130,170,255,${Math.min(0.3, (c.avg_correlation || 0) * 0.35)})`,
                                        display: 'flex', justifyContent: 'center', alignItems: 'center',
                                        fontSize: 14, fontWeight: 800, color: '#82aaff',
                                    }}>
                                        {idx + 1}
                                    </div>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                            <span style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>
                                                {c.lead_symbol?.replace('USDT', '') || `클러스터 #${c.cluster_id}`}
                                            </span>
                                            <span style={{
                                                fontSize: 11, padding: '2px 8px', borderRadius: 4,
                                                background: 'rgba(0,230,118,0.1)', color: '#00e676',
                                                fontWeight: 600,
                                            }}>
                                                {c.coin_count}개 코인
                                            </span>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: '#888' }}>
                                            <span>상관 {formatCorr(c.avg_correlation)}</span>
                                            <span>대장 {c.lead_symbol?.replace('USDT', '') || '—'} ({formatPct(c.lead_change_pct)})</span>
                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: 18, fontWeight: 800, color: pctColor(c.avg_high_change_pct) }}>
                                            {formatPct(c.avg_high_change_pct)}
                                        </div>
                                        <div style={{ fontSize: 11, color: '#666' }}>
                                            강도 {c.strength_score.toFixed(1)}
                                        </div>
                                    </div>
                                    <span style={{ color: '#666' }}>
                                        {expandedClusterId === c.cluster_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                    </span>
                                </div>
                            </div>

                            {/* Expanded Members */}
                            {expandedClusterId === c.cluster_id && (
                                <div style={{
                                    background: 'rgba(130,170,255,0.02)',
                                    borderTop: '1px solid #1c2333',
                                    padding: '12px 20px 16px',
                                }}>
                                    {membersLoading ? (
                                        <div style={{ color: '#666', fontSize: 12, padding: 8 }}>로딩 중...</div>
                                    ) : (
                                        <>
                                            {/* Member table header */}
                                            <div style={{
                                                display: 'grid',
                                                gridTemplateColumns: '1fr 100px 100px',
                                                padding: '6px 14px',
                                                fontSize: 11,
                                                color: '#666',
                                                fontWeight: 600,
                                                borderBottom: '1px solid #1a1a1a',
                                                marginBottom: 4,
                                            }}>
                                                <span>심볼</span>
                                                <span style={{ textAlign: 'right' }}>변동률</span>
                                                <span style={{ textAlign: 'right' }}>대장주 상관</span>
                                            </div>
                                            {clusterMembers.map((m) => (
                                                <div key={m.symbol} style={{
                                                    display: 'grid',
                                                    gridTemplateColumns: '1fr 100px 100px',
                                                    alignItems: 'center',
                                                    padding: '10px 14px',
                                                    background: '#0a0a0a',
                                                    borderRadius: 8,
                                                    border: '1px solid #1a1a1a',
                                                    marginBottom: 4,
                                                }}>
                                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>
                                                        {m.symbol.replace('USDT', '')}
                                                    </div>
                                                    <div style={{ textAlign: 'right', fontSize: 13, fontWeight: 600, color: pctColor(m.daily_change_pct) }}>
                                                        {formatPct(m.daily_change_pct)}
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <span style={{
                                                            fontSize: 12,
                                                            fontWeight: 600,
                                                            color: (m.correlation_to_lead || 0) >= 0.85 ? '#82aaff' : '#aaa',
                                                        }}>
                                                            {formatCorr(m.correlation_to_lead)}
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ==================== Main ThemePage ====================
export default function ThemePage() {
    const [activeTab, setActiveTab] = useState<TabType>('static');

    const tabs: { key: TabType; label: string; tooltip: string }[] = [
        {
            key: 'static',
            label: '정적 테마',
            tooltip: '사전 정의된 테마(밈코인, AI, 레이어1 등) 기반 상대강도(RS). 10분마다 갱신.',
        },
        {
            key: 'dynamic',
            label: '동적 테마',
            tooltip: '14일 시장 중립 상관관계 기반 계층적 클러스터링. BTC 효과를 제거하고 진짜 같이 움직이는 코인 그룹 발견. 매일 KST 06:00 갱신.',
        },
    ];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Tab Switcher */}
            <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid #1c2333', paddingBottom: 0 }}>
                {tabs.map((tab) => (
                    <Tooltip key={tab.key} content={tab.tooltip}>
                        <button
                            onClick={() => setActiveTab(tab.key)}
                            style={{
                                padding: '10px 20px',
                                fontSize: 13,
                                fontWeight: activeTab === tab.key ? 700 : 500,
                                color: activeTab === tab.key ? '#82aaff' : '#888',
                                background: 'transparent',
                                border: 'none',
                                borderBottom: activeTab === tab.key ? '2px solid #82aaff' : '2px solid transparent',
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                                marginBottom: -1,
                            }}
                        >
                            {tab.label}
                        </button>
                    </Tooltip>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'static' ? <StaticThemeTab /> : <DynamicThemeTab />}
        </div>
    );
}
