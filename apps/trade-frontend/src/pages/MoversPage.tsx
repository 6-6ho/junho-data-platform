import { useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMovers } from '../api/client';
import { TrendingUp, Zap } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { useNavigate } from 'react-router-dom';

const MAX_NOTIFIED_CACHE = 100;

export default function MoversPage() {
    const navigate = useNavigate();
    const { addToast } = useToast();
    const notifiedRef = useRef<Set<string>>(new Set());
    const isFirstLoadRef = useRef(true);

    const { data: movers, isLoading, dataUpdatedAt } = useQuery({
        queryKey: ['movers'],
        queryFn: () => fetchMovers(),
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
    });

    useEffect(() => {
        if (!movers || movers.length === 0) return;

        if (isFirstLoadRef.current) {
            movers.forEach((m: any) => {
                if (m.type === 'rise') {
                    notifiedRef.current.add(`${m.symbol}-${m.event_time}`);
                }
            });
            isFirstLoadRef.current = false;
            return;
        }

        movers.forEach((m: any) => {
            if (m.type === 'rise' && m.change_pct_window >= 5.0) {
                const key = `${m.symbol}-${m.event_time}`;
                if (!notifiedRef.current.has(key)) {
                    addToast(`${m.symbol} is pumping! (+${m.change_pct_window.toFixed(2)}%)`, 'rise', 5000);
                    notifiedRef.current.add(key);
                    if (notifiedRef.current.size > MAX_NOTIFIED_CACHE) {
                        const entries = Array.from(notifiedRef.current);
                        notifiedRef.current = new Set(entries.slice(-MAX_NOTIFIED_CACHE / 2));
                    }
                }
            }
        });
    }, [movers, addToast, dataUpdatedAt]);

    if (isLoading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
                <div className="loading-spinner" />
            </div>
        );
    }

    const riseList = movers?.filter((m: any) => m.type === 'rise') || [];
    const volList = movers?.filter((m: any) => m.type === 'high_vol_up') || [];

    const handleSelect = (symbol: string) => navigate(`/crypto/symbol/${symbol}`);

    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-5)', height: 'calc(100vh - 120px)' }}>
            {/* Risers Column */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div className="card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <TrendingUp size={16} style={{ color: 'var(--color-success)' }} />
                        <span className="card-title">Risers</span>
                    </div>
                    <span className="card-count">{riseList.length} PAIRS</span>
                </div>
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    {riseList.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">📈</div>
                            <div className="empty-state-text">No risers detected</div>
                        </div>
                    ) : (
                        riseList.map((item: any) => (
                            <div
                                key={item.symbol + item.event_time}
                                className="mover-item"
                                onClick={() => handleSelect(item.symbol)}
                            >
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                        <span className="mover-symbol">
                                            {item.symbol.replace('USDT', '')}
                                            <span className="mover-base">/USDT</span>
                                        </span>
                                        <span className="badge badge-perp">PERP</span>
                                    </div>
                                    <div className="mover-meta">
                                        <span className="badge badge-rise">{item.status}</span>
                                        <span className="mover-time">
                                            {item.window || '5m'} · {new Date(item.event_time).toLocaleTimeString('ko-KR', {
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </span>
                                    </div>
                                </div>
                                <span className={`mover-change ${item.change_pct_window >= 0 ? 'up' : 'down'}`}>
                                    {item.change_pct_window > 0 ? '+' : ''}{item.change_pct_window.toFixed(2)}%
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* High Volume Column */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div className="card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <Zap size={16} style={{ color: 'var(--accent-primary)' }} />
                        <span className="card-title">High Volume</span>
                    </div>
                    <span className="card-count">{volList.length} PAIRS</span>
                </div>
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    {volList.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">⚡</div>
                            <div className="empty-state-text">No volume spikes detected</div>
                        </div>
                    ) : (
                        volList.map((item: any) => (
                            <div
                                key={item.symbol + item.event_time}
                                className="mover-item"
                                onClick={() => handleSelect(item.symbol)}
                            >
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                        <span className="mover-symbol">
                                            {item.symbol.replace('USDT', '')}
                                            <span className="mover-base">/USDT</span>
                                        </span>
                                        <span className="badge badge-perp">PERP</span>
                                    </div>
                                    <div className="mover-meta">
                                        <span className="badge badge-vol">{item.status}</span>
                                        <span className="mover-time">
                                            {new Date(item.event_time).toLocaleTimeString('ko-KR', {
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </span>
                                    </div>
                                </div>
                                <span className={`mover-change ${item.change_pct_window >= 0 ? 'up' : 'down'}`}>
                                    {item.change_pct_window > 0 ? '+' : ''}{item.change_pct_window.toFixed(2)}%
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
