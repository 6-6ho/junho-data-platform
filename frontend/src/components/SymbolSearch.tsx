import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';

export default function SymbolSearch() {
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const navigate = useNavigate();

    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            const symbol = query.toUpperCase().replace(/\s/g, '');
            const finalSymbol = symbol.endsWith('USDT') ? symbol : `${symbol}USDT`;
            navigate(`/symbol/${finalSymbol}`);
            setQuery('');
            setIsOpen(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            setIsOpen(false);
            setQuery('');
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                style={{
                    background: 'var(--binance-bg-3)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '4px',
                    padding: '6px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: 'var(--text-tertiary)',
                    cursor: 'pointer',
                    fontSize: '13px',
                    transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--binance-yellow)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
            >
                <Search size={14} />
                <span>Search Symbol</span>
                <kbd style={{
                    background: 'var(--binance-bg-2)',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontSize: '10px',
                    color: 'var(--text-tertiary)'
                }}>/</kbd>
            </button>
        );
    }

    return (
        <form onSubmit={handleSubmit} style={{ position: 'relative' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                background: 'var(--binance-bg-3)',
                border: '1px solid var(--binance-yellow)',
                borderRadius: '4px',
                padding: '4px 8px',
                gap: '8px'
            }}>
                <Search size={14} style={{ color: 'var(--binance-yellow)' }} />
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="BTC, ETH, SOL..."
                    style={{
                        background: 'transparent',
                        border: 'none',
                        outline: 'none',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                        width: '120px'
                    }}
                />
                <button
                    type="button"
                    onClick={() => { setIsOpen(false); setQuery(''); }}
                    style={{
                        background: 'none',
                        border: 'none',
                        padding: '2px',
                        cursor: 'pointer',
                        color: 'var(--text-tertiary)'
                    }}
                >
                    <X size={14} />
                </button>
            </div>
        </form>
    );
}
