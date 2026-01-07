import { useState } from 'react';
import { Search } from 'lucide-react';
import clsx from 'clsx';

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
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <div className="relative">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Search Symbol (e.g. BTCUSDT)"
                    className="pl-9 pr-4 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors w-48 font-mono uppercase"
                />
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            </div>
            <button
                type="submit"
                disabled={!input.trim() || input.trim().toUpperCase() === currentSymbol}
                className={clsx(
                    "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                    !input.trim() || input.trim().toUpperCase() === currentSymbol
                        ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                        : "bg-blue-600 text-white hover:bg-blue-500"
                )}
            >
                Load
            </button>
        </form>
    );
}
