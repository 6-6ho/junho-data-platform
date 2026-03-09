import { useState, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, Zap, Clock } from 'lucide-react';
import { Tooltip } from '../components/Tooltip';

const API_BASE = '/api/theme';

interface DynamicCluster {
    cluster_id: number;
    created_date: string;
    coin_count: number;
    strength_score: number;
    avg_high_time: string;
    time_spread_minutes: number;
    avg_high_change_pct: number;
}

interface DynamicMember {
    symbol: string;
    high_time: string;
    high_price: number;
    high_change_pct: number;
    change_pct_24h: number | null;
    vol_ratio: number | null;
}

export default function DynamicThemePage() {
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

    const formatPct = (v: number | null) => v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
    const pctColor = (v: number | null) => v == null ? '#888' : v >= 0 ? '#00e676' : '#ff5252';
    const formatTime = (isoStr: string) => {
        try {
            return new Date(isoStr).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
        } catch { return isoStr; }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
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
                        <Tooltip content="같은 날 동시에 상승한 코인들을 자동 클러스터링합니다. 25~26년 신규 상장 코인 중 반복적으로 함께 움직이는 종목은 같은 세력이거나 숨겨진 테마일 가능성이 높습니다. 연관성을 누적해 새로운 테마를 발견하는 것이 목표입니다.">
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
                                        background: `rgba(130,170,255,${Math.min(0.3, c.strength_score / 50)})`,
                                        display: 'flex', justifyContent: 'center', alignItems: 'center',
                                        fontSize: 14, fontWeight: 800, color: '#82aaff',
                                    }}>
                                        {idx + 1}
                                    </div>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                            <span style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>
                                                클러스터 #{c.cluster_id}
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
                                            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                                <Clock size={11} />
                                                고점 {formatTime(c.avg_high_time)}
                                            </span>
                                            <span>분산 {c.time_spread_minutes.toFixed(0)}분</span>
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
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 8 }}>
                                            {clusterMembers.map((m) => (
                                                <div key={m.symbol} style={{
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    alignItems: 'center',
                                                    padding: '10px 14px',
                                                    background: '#0a0a0a',
                                                    borderRadius: 8,
                                                    border: '1px solid #1a1a1a',
                                                }}>
                                                    <div>
                                                        <div style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>
                                                            {m.symbol.replace('USDT', '')}
                                                        </div>
                                                        <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                                                            고점 {formatTime(m.high_time)}
                                                        </div>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <div style={{ fontSize: 13, fontWeight: 600, color: pctColor(m.high_change_pct) }}>
                                                            {formatPct(m.high_change_pct)}
                                                        </div>
                                                        {m.change_pct_24h != null && (
                                                            <div style={{ fontSize: 11, color: pctColor(m.change_pct_24h) }}>
                                                                24h {formatPct(m.change_pct_24h)}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
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
