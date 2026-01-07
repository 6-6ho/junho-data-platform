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
                color: 'var(--text-muted)'
            }} className="loading">
                Loading market data...
            </div>
        );
    }

    const riseList = movers?.filter((m: any) => m.type === 'rise') || [];
    const volList = movers?.filter((m: any) => m.type === 'high_vol_up') || [];

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '24px'
        }}>
            <MoverColumn
                title="Rising"
                subtitle="Price momentum"
                icon={<TrendingUp size={18} style={{ color: 'var(--accent-green)' }} />}
                items={riseList}
                onSelect={onSymbolSelect}
                accentColor="green"
            />
            <MoverColumn
                title="High Volume"
                subtitle="Volume spike"
                icon={<Zap size={18} style={{ color: 'var(--accent-amber)' }} />}
                items={volList}
                onSelect={onSymbolSelect}
                accentColor="amber"
            />
        </div>
    );
}

function MoverColumn({ title, subtitle, icon, items, onSelect, accentColor }: any) {
    return (
        <div className="card">
            {/* Header */}
            <div className="card-header" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {icon}
                    <div>
                        <h2 style={{
                            fontSize: '16px',
                            fontWeight: 600,
                            margin: 0,
                            color: 'var(--text-primary)'
                        }}>{title}</h2>
                        <span style={{
                            fontSize: '12px',
                            color: 'var(--text-muted)'
                        }}>{subtitle}</span>
                    </div>
                </div>
                <span style={{
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    background: 'var(--bg-primary)',
                    padding: '4px 10px',
                    borderRadius: '20px'
                }}>
                    {items.length}
                </span>
            </div>

            {/* Items */}
            <div style={{ maxHeight: '75vh', overflowY: 'auto' }}>
                {items.length === 0 ? (
                    <div style={{
                        padding: '60px 20px',
                        textAlign: 'center',
                        color: 'var(--text-muted)',
                        fontSize: '14px'
                    }}>
                        No events yet
                    </div>
                ) : (
                    items.map((item: any) => (
                        <div
                            key={item.symbol + item.event_time}
                            onClick={() => onSelect(item.symbol)}
                            className="mover-item"
                        >
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start',
                                marginBottom: '8px'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{
                                        fontWeight: 600,
                                        fontSize: '15px',
                                        color: 'var(--text-primary)'
                                    }}>
                                        {item.symbol}
                                    </span>
                                    <span className="badge badge-perp">PERP</span>
                                </div>

                                <div style={{ textAlign: 'right' }}>
                                    {item.type === 'rise' ? (
                                        <div>
                                            <span style={{
                                                fontFamily: 'monospace',
                                                fontWeight: 500,
                                                fontSize: '15px',
                                                color: item.change_pct_window >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                                            }}>
                                                {item.change_pct_window > 0 ? '+' : ''}{item.change_pct_window?.toFixed(2)}%
                                            </span>
                                            <div style={{
                                                fontSize: '11px',
                                                color: 'var(--text-muted)',
                                                marginTop: '2px'
                                            }}>
                                                {item.window || '5m'} change
                                            </div>
                                        </div>
                                    ) : (
                                        <span style={{
                                            fontFamily: 'monospace',
                                            fontWeight: 500,
                                            color: item.change_pct_24h >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                                        }}>
                                            {item.change_pct_24h > 0 ? '+' : ''}{item.change_pct_24h?.toFixed(2)}%
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                            }}>
                                <span className={`badge badge-${accentColor === 'green' ? 'rise' : 'vol'}`}>
                                    {item.status}
                                </span>
                                <span style={{
                                    fontSize: '12px',
                                    color: 'var(--text-muted)'
                                }}>
                                    {new Date(item.event_time).toLocaleTimeString('ko-KR', {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        second: '2-digit'
                                    })}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
