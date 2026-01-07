import { useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMovers } from '../api/client';
import { TrendingUp, Zap } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { useNavigate } from 'react-router-dom';

export default function MoversPage() {
    const navigate = useNavigate();
    const { addToast } = useToast();
    const notifiedRef = useRef<Set<string>>(new Set());

    const { data: movers, isLoading } = useQuery({
        queryKey: ['movers'],
        queryFn: () => fetchMovers(),
        refetchInterval: 5000,
    });

    // Check for high risers (>5%) and toast
    useEffect(() => {
        if (!movers) return;

        // On first load, just populate the set without alerting
        if (notifiedRef.current.size === 0 && movers.length > 0) {
            movers.forEach((m: any) => {
                if (m.type === 'rise') {
                    const key = `${m.symbol}-${m.event_time}`;
                    notifiedRef.current.add(key);
                }
            });
            return;
        }

        // Subsequent updates
        movers.forEach((m: any) => {
            if (m.type === 'rise' && m.change_pct_window >= 5.0) {
                const key = `${m.symbol}-${m.event_time}`;

                if (!notifiedRef.current.has(key)) {
                    addToast(`${m.symbol} is pumping! (+${m.change_pct_window.toFixed(2)}%)`, 'rise', 5000);
                    notifiedRef.current.add(key);
                }
            }
        });
    }, [movers, addToast]);

    if (isLoading) {
        return (
            <div style={{
                padding: '60px',
                textAlign: 'center',
                color: 'var(--text-tertiary)'
            }} className="loading">
                Loading...
            </div>
        );
    }

    const riseList = movers?.filter((m: any) => m.type === 'rise') || [];
    const volList = movers?.filter((m: any) => m.type === 'high_vol_up') || [];

    const handleSelect = (symbol: string) => {
        navigate(`/symbol/${symbol}`);
    };

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            gap: '16px'
        }}>
            <MoverColumn
                title="Risers"
                icon={<TrendingUp size={16} style={{ color: 'var(--binance-green)' }} />}
                items={riseList}
                onSelect={handleSelect}
                type="rise"
            />
            <MoverColumn
                title="High Volume"
                icon={<Zap size={16} style={{ color: 'var(--binance-yellow)' }} />}
                items={volList}
                onSelect={handleSelect}
                type="vol"
            />
        </div>
    );
}

function MoverColumn({ title, icon, items, onSelect, type }: any) {
    return (
        <div className="card">
            {/* Header */}
            <div className="card-header" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {icon}
                    <span style={{
                        fontSize: '14px',
                        fontWeight: 600,
                        color: 'var(--text-primary)'
                    }}>{title}</span>
                </div>
                <span style={{
                    fontSize: '12px',
                    color: 'var(--text-tertiary)',
                }}>
                    {items.length} pairs
                </span>
            </div>

            {/* Column Headers */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                padding: '8px 16px',
                borderBottom: '1px solid var(--border-color)',
                background: 'var(--binance-bg-2)'
            }}>
                <span className="table-header">Pair</span>
                <span className="table-header" style={{ textAlign: 'right' }}>Change</span>
            </div>

            {/* Items */}
            <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                {items.length === 0 ? (
                    <div style={{
                        padding: '40px 20px',
                        textAlign: 'center',
                        color: 'var(--text-tertiary)',
                        fontSize: '13px'
                    }}>
                        No data
                    </div>
                ) : (
                    items.map((item: any) => (
                        <div
                            key={item.symbol + item.event_time}
                            onClick={() => onSelect(item.symbol)}
                            className="mover-item"
                        >
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: '1fr auto',
                                alignItems: 'center',
                            }}>
                                {/* Left: Symbol & Status */}
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                        <span className="symbol-pair">
                                            {item.symbol.replace('USDT', '')}
                                            <span className="symbol-base">/USDT</span>
                                        </span>
                                        <span className="badge badge-perp">PERP</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span className={`badge badge-${type === 'rise' ? 'rise' : 'vol'}`}>
                                            {item.status}
                                        </span>
                                        <span style={{
                                            fontSize: '11px',
                                            color: 'var(--text-tertiary)'
                                        }}>
                                            {item.window || '5m'} · {new Date(item.event_time).toLocaleTimeString('ko-KR', {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                second: '2-digit'
                                            })}
                                        </span>
                                    </div>
                                </div>

                                {/* Right: Percentage */}
                                <div style={{ textAlign: 'right' }}>
                                    {item.type === 'rise' ? (
                                        <span className={`pct-change ${item.change_pct_window >= 0 ? 'pct-up' : 'pct-down'}`}>
                                            {item.change_pct_window > 0 ? '+' : ''}{item.change_pct_window?.toFixed(2)}%
                                        </span>
                                    ) : (
                                        <span className={`pct-change ${item.change_pct_24h >= 0 ? 'pct-up' : 'pct-down'}`}>
                                            {item.change_pct_24h > 0 ? '+' : ''}{item.change_pct_24h?.toFixed(2)}%
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
