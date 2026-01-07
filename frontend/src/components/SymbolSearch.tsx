import { useState } from 'react';
import { Search } from 'lucide-react';

interface SymbolSearchProps {
    onSearch: (symbol: string) => void;
    currentSymbol: string;
}

export default function SymbolSearch({ onSearch, currentSymbol }: SymbolSearchProps) {
    const [input, setInput] = useState(currentSymbol);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            onSearch(input.trim().toUpperCase());
        }
    };

    return (
        <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ position: 'relative' }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Search Symbol"
                    style={{
                        paddingLeft: '32px',
                        paddingRight: '12px',
                        paddingTop: '6px',
                        paddingBottom: '6px',
                        background: 'var(--binance-bg-3)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '4px',
                        fontSize: '13px',
                        color: 'var(--text-primary)',
                        width: '160px',
                        fontFamily: 'monospace',
                        textTransform: 'uppercase',
                        outline: 'none'
                    }}
                />
                <Search
                    size={14}
                    style={{
                        position: 'absolute',
                        left: '10px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: 'var(--text-tertiary)'
                    }}
                />
            </div>
            <button
                type="submit"
                disabled={!input.trim() || input.trim().toUpperCase() === currentSymbol}
                style={{
                    padding: '6px 12px',
                    borderRadius: '4px',
                    fontSize: '13px',
                    fontWeight: 500,
                    border: 'none',
                    cursor: (!input.trim() || input.trim().toUpperCase() === currentSymbol) ? 'not-allowed' : 'pointer',
                    background: (!input.trim() || input.trim().toUpperCase() === currentSymbol)
                        ? 'var(--binance-bg-3)'
                        : 'var(--binance-yellow)',
                    color: (!input.trim() || input.trim().toUpperCase() === currentSymbol)
                        ? 'var(--text-tertiary)'
                        : '#0b0e11',
                    transition: 'all 0.15s ease'
                }}
            >
                Go
            </button>
        </form>
    );
}
