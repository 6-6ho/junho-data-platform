import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
    label: string;
    value: string;
    subValue?: React.ReactNode;
    icon: LucideIcon;
    iconColor: string;
    trend?: {
        value?: string;
        label: string;
        isPositive: boolean;
    };
    tooltip?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon: Icon, iconColor, trend }) => {
    return (
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '1.25rem', gap: '1.5rem' }}>
            {/* Top Row: Icon and Badge */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div style={{
                    padding: '8px',
                    borderRadius: '12px',
                    background: `rgba(${iconColor === '#3b82f6' ? '59, 130, 246' : iconColor === '#10b981' ? '16, 185, 129' : iconColor === '#f59e0b' ? '245, 158, 11' : iconColor === '#ef4444' ? '239, 68, 68' : '119, 93, 208'}, 0.1)`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <Icon size={24} color={iconColor} />
                </div>

                {trend && (
                    <div className={`stat-change ${trend.isPositive ? 'positive' : 'negative'}`} style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        background: trend.isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        border: `1px solid ${trend.isPositive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
                    }}>
                        <span style={{
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            color: trend.isPositive ? '#10b981' : '#ef4444'
                        }}>
                            {trend.label}
                        </span>
                    </div>
                )}
            </div>

            {/* Bottom Row: Label and Value */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                    {value}
                </div>
            </div>
        </div>
    );
};

export default StatCard;
