import { useQuery } from '@tanstack/react-query';
import { fetchMovers } from '../api/client';
import { TrendingUp, Zap } from 'lucide-react';

interface MoversPageProps {
    onSymbolSelect: (symbol: string) => void;
}

export default function MoversPage({ onSymbolSelect }: MoversPageProps) {
    const { data: movers, isLoading } = useQuery({
        queryKey: ['movers'],
        queryFn: () => fetchMovers(),
        refetchInterval: 5000,
    });

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
                onSelect={onSymbolSelect}
                type="rise"
            />
            <MoverColumn
                title="High Volume"
                icon={<Zap size={16} style={{ color: 'var(--binance-yellow)' }} />}
                items={volList}
                onSelect={onSymbolSelect}
                type="vol"
            />
        </div>
    );
}

function MoverColumn({ title, icon, items, onSelect, type }: any) {
    return (
        <div className="card">
            {/* Header - Binance table header style */}
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

            {/* Column Headers - Binance style */}
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
                                                minute: '2-digit'
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
