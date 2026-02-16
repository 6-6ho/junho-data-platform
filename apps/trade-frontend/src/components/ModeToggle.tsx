import { useState, useEffect, useRef } from 'react';

const API_BASE = '/api/system';

type Mode = 'trade' | 'shop' | 'off';

interface ModeInfo {
    mode: Mode;
    updated_at: string | null;
}

const MODE_CONFIG: Record<Mode, { label: string; icon: string; color: string; bg: string }> = {
    trade: { label: 'Trade', icon: '📈', color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
    shop: { label: 'Shop', icon: '🛍️', color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
    off: { label: 'Off', icon: '⏸️', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
};

export default function ModeToggle() {
    const [currentMode, setCurrentMode] = useState<Mode>('off');
    const [isOpen, setIsOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchMode();
        const interval = setInterval(fetchMode, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    async function fetchMode() {
        try {
            const res = await fetch(`${API_BASE}/mode`);
            const data: ModeInfo = await res.json();
            setCurrentMode(data.mode as Mode);
        } catch {
            // ignore
        }
    }

    async function switchMode(newMode: Mode) {
        if (newMode === currentMode) {
            setIsOpen(false);
            return;
        }

        setIsLoading(true);
        try {
            const res = await fetch(`${API_BASE}/mode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: newMode }),
            });
            if (res.ok) {
                setCurrentMode(newMode);
            }
        } catch {
            // ignore
        } finally {
            setIsLoading(false);
            setIsOpen(false);
        }
    }

    const config = MODE_CONFIG[currentMode];

    return (
        <div ref={dropdownRef} style={{ position: 'relative' }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={isLoading}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: `1.5px solid ${config.color}`,
                    background: config.bg,
                    color: config.color,
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    opacity: isLoading ? 0.6 : 1,
                }}
            >
                <span style={{ fontSize: '14px' }}>{config.icon}</span>
                <span>{config.label}</span>
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={{
                    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s ease',
                }}>
                    <path d="M2 4L5 7L8 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            </button>

            {isOpen && (
                <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 6px)',
                    right: 0,
                    background: '#1a1a2e',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '10px',
                    padding: '4px',
                    minWidth: '140px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    zIndex: 100,
                }}>
                    {(Object.keys(MODE_CONFIG) as Mode[]).map((mode) => {
                        const mc = MODE_CONFIG[mode];
                        const isActive = mode === currentMode;
                        return (
                            <button
                                key={mode}
                                onClick={() => switchMode(mode)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    width: '100%',
                                    padding: '8px 12px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    background: isActive ? mc.bg : 'transparent',
                                    color: isActive ? mc.color : '#a0a0b0',
                                    fontSize: '13px',
                                    fontWeight: isActive ? 600 : 400,
                                    cursor: 'pointer',
                                    transition: 'all 0.1s ease',
                                    textAlign: 'left',
                                }}
                                onMouseEnter={(e) => {
                                    if (!isActive) (e.target as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
                                }}
                                onMouseLeave={(e) => {
                                    if (!isActive) (e.target as HTMLElement).style.background = 'transparent';
                                }}
                            >
                                <span style={{ fontSize: '14px' }}>{mc.icon}</span>
                                <span>{mc.label}</span>
                                {isActive && (
                                    <span style={{ marginLeft: 'auto', fontSize: '11px', opacity: 0.7 }}>●</span>
                                )}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
