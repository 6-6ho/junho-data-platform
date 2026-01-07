import { fetchAlerts } from '../api/client';
import { useQuery } from '@tanstack/react-query';
import { Bell } from 'lucide-react';

export default function AlertsSidebar({ symbol }: { symbol: string }) {
    const { data: alerts } = useQuery({
        queryKey: ['alerts', symbol],
        queryFn: () => fetchAlerts(symbol),
        refetchInterval: 5000
    });

    return (
        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Bell size={14} style={{ color: 'var(--binance-yellow)' }} />
                <span style={{ fontSize: '14px', fontWeight: 600 }}>Alerts</span>
            </div>

            {/* Alert List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
                {alerts && alerts.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {alerts.map((alert: any) => (
                            <div
                                key={alert.event_time + alert.line_id}
                                style={{
                                    fontSize: '13px',
                                    background: 'var(--binance-bg-3)',
                                    padding: '10px',
                                    borderRadius: '4px',
                                    border: '1px solid var(--border-color)'
                                }}
                            >
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    marginBottom: '6px',
                                    fontSize: '11px',
                                    color: 'var(--text-tertiary)'
                                }}>
                                    <span>
                                        {new Date(alert.event_time).toLocaleTimeString('ko-KR', {
                                            hour: '2-digit',
                                            minute: '2-digit'
                                        })}
                                    </span>
                                    <span style={{
                                        fontWeight: 600,
                                        textTransform: 'uppercase',
                                        color: alert.direction === 'break_up'
                                            ? 'var(--binance-green)'
                                            : 'var(--binance-red)'
                                    }}>
                                        {alert.direction === 'break_up' ? '↑ Break Up' : '↓ Break Down'}
                                    </span>
                                </div>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                }}>
                                    <span style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                                        ${parseFloat(alert.price).toLocaleString()}
                                    </span>
                                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                                        Line: ${parseFloat(alert.line_price).toLocaleString()}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div style={{
                        textAlign: 'center',
                        color: 'var(--text-tertiary)',
                        fontSize: '13px',
                        marginTop: '40px'
                    }}>
                        No alerts yet
                    </div>
                )}
            </div>
        </div>
    );
}
