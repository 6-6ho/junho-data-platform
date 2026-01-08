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

    // Global keyboard shortcut
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === '/' && !isOpen) {
                e.preventDefault();
                setIsOpen(true);
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
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
            <button onClick={() => setIsOpen(true)} className="search-btn">
                <Search size={14} />
                <span>Search Symbol</span>
                <span className="search-kbd">/</span>
            </button>
        );
    }

    return (
        <form onSubmit={handleSubmit}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                background: 'var(--bg-overlay)',
                border: '1px solid var(--accent-primary)',
                borderRadius: 'var(--radius-sm)',
                padding: 'var(--space-2) var(--space-3)',
                boxShadow: 'var(--shadow-glow)'
            }}>
                <Search size={14} style={{ color: 'var(--accent-primary)' }} />
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
                        fontSize: 'var(--text-sm)',
                        width: '140px',
                        fontFamily: 'inherit'
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
                        color: 'var(--text-tertiary)',
                        display: 'flex'
                    }}
                >
                    <X size={14} />
                </button>
            </div>
        </form>
    );
}
