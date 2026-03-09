import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Flame, BarChart3, Layers } from 'lucide-react';
import { Tooltip } from '../components/Tooltip';

const API_BASE = '/api/theme';

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

export default function ThemePage() {
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
    const formatPct = (v: number | null) => v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
    const pctColor = (v: number | null) => v == null ? '#888' : v >= 0 ? '#00e676' : '#ff5252';

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
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
