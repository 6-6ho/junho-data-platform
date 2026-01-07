import ChartWrapper from '../components/ChartWrapper';
import AlertsSidebar from '../components/AlertsSidebar';
import SymbolSearch from '../components/SymbolSearch';

interface ChartPageProps {
    symbol: string;
    onSymbolSelect: (symbol: string) => void;
}

export default function ChartPage({ symbol, onSymbolSelect }: ChartPageProps) {
    return (
        <div className="h-[calc(100vh-80px)] flex flex-col gap-4">
            <div className="flex justify-between items-center px-4">
                <h2 className="text-xl font-bold text-slate-200 flex items-center gap-3">
                    {symbol}
                    <span className="text-xs font-normal text-slate-500 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">PERP</span>
                </h2>
                <SymbolSearch currentSymbol={symbol} onSearch={onSymbolSelect} />
            </div>
            <div className="flex-1 flex border border-slate-800 rounded-xl overflow-hidden shadow-2xl bg-slate-900">
                <div className="flex-1 relative">
                    <ChartWrapper symbol={symbol} />
                </div>
                <AlertsSidebar symbol={symbol} />
            </div>
        </div>
    );
}
