import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';

export default function SymbolSearch() {
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [symbols, setSymbols] = useState<{ symbol: string, price: string }[]>([]);
    const [filteredSymbols, setFilteredSymbols] = useState<{ symbol: string, price: string }[]>([]);
    const [activeIndex, setActiveIndex] = useState(-1);

    const inputRef = useRef<HTMLInputElement>(null);
    const resultRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();

    // Fetch symbols on open
    useEffect(() => {
        if (isOpen && symbols.length === 0) {
            fetch('/api/analysis/symbols')
                .then(res => res.json())
                .then(data => setSymbols(data))
                .catch(err => console.error(err));
        }
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    // Filter logic
    useEffect(() => {
        if (!query) {
            setFilteredSymbols([]);
            return;
        }
        const lowerQ = query.toLowerCase();
        const matches = symbols
            .filter(s => s.symbol.toLowerCase().includes(lowerQ))
            .slice(0, 10); // Limit to 10 results
        setFilteredSymbols(matches);
        setActiveIndex(matches.length > 0 ? 0 : -1);
    }, [query, symbols]);

    // Global keyboard shortcut
    useEffect(() => {
        const handleGlobalKeyDown = (e: KeyboardEvent) => {
            if (e.key === '/' && !isOpen) {
                e.preventDefault();
                setIsOpen(true);
            }
        };
        document.addEventListener('keydown', handleGlobalKeyDown);
        return () => document.removeEventListener('keydown', handleGlobalKeyDown);
    }, [isOpen]);

    const handleSelect = (symbol: string) => {
        navigate(`/symbol/${symbol}`);
        setQuery('');
        setIsOpen(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            setIsOpen(false);
            setQuery('');
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex(prev => (prev < filteredSymbols.length - 1 ? prev + 1 : prev));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex(prev => (prev > 0 ? prev - 1 : prev));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && filteredSymbols[activeIndex]) {
                handleSelect(filteredSymbols[activeIndex].symbol);
            } else if (query) {
                // specific direct input fallback
                handleSelect(query.toUpperCase().endsWith('USDT') ? query.toUpperCase() : query.toUpperCase() + 'USDT');
            }
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
        <div>
            <div style={{
                position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9998
            }} onClick={() => setIsOpen(false)} />

            <div style={{
                position: 'fixed',
                top: '20%',
                left: '50%',
                transform: 'translateX(-50%)',
                width: '400px',
                zIndex: 9999,
                background: '#1a1a1c',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                padding: 'var(--space-2)'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-2)',
                    borderBottom: filteredSymbols.length > 0 ? '1px solid var(--border-color)' : 'none'
                }}>
                    <Search size={18} style={{ color: 'var(--accent-primary)' }} />
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Search standard symbol (e.g. BTC, SOL)..."
                        style={{
                            background: 'transparent',
                            border: 'none',
                            outline: 'none',
                            color: 'var(--text-primary)',
                            fontSize: '16px',
                            width: '100%',
                            fontFamily: 'inherit'
                        }}
                    />
                </div>

                {filteredSymbols.length > 0 && (
                    <div ref={resultRef} style={{ maxHeight: '300px', overflowY: 'auto', marginTop: '4px' }}>
                        {filteredSymbols.map((item, idx) => (
                            <div
                                key={item.symbol}
                                onClick={() => handleSelect(item.symbol)}
                                onMouseEnter={() => setActiveIndex(idx)}
                                style={{
                                    padding: '10px 12px',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    cursor: 'pointer',
                                    background: idx === activeIndex ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                                    color: idx === activeIndex ? '#fff' : 'var(--text-secondary)',
                                    borderRadius: '4px'
                                }}
                            >
                                <span style={{ fontWeight: 600 }}>{item.symbol.replace('USDT', '')}</span>
                                <span style={{ opacity: 0.7 }}>${parseFloat(item.price).toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
