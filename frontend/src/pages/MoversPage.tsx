import { useQuery } from '@tanstack/react-query';
import { fetchMovers } from '../api/client';
import { ArrowUpRight, SignalHigh } from 'lucide-react';
import clsx from 'clsx';

interface MoversPageProps {
    onSymbolSelect: (symbol: string) => void;
}

export default function MoversPage({ onSymbolSelect }: MoversPageProps) {
    const { data: movers, isLoading } = useQuery({
        queryKey: ['movers'],
        queryFn: () => fetchMovers(),
        refetchInterval: 5000, // Auto refresh every 5s
    });

    if (isLoading) return <div className="p-8 text-center text-slate-500 animate-pulse">Loading market data...</div>;

    // Split into Rise and HighVolUp
    // Note: Backend returns flat list mixed. We filter client side for better UI separation if needed 
    // or just show mixed list sorted by time.
    // Spec says: Left (Rise), Right (HighVolUp).
    // But our backend currently just dumps everything into 'movers_latest'.
    // Let's assume 'type' field exists in response.

    const riseList = movers?.filter((m: any) => m.type === 'rise') || [];
    const volList = movers?.filter((m: any) => m.type === 'high_vol_up') || [];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <MoverColumn
                title="Rise (Top 20)"
                icon={<ArrowUpRight className="text-emerald-400" />}
                items={riseList}
                onSelect={onSymbolSelect}
            />
            <MoverColumn
                title="High Vol Up (Top 20)"
                icon={<SignalHigh className="text-amber-400" />}
                items={volList}
                onSelect={onSymbolSelect}
            />
        </div>
    );
}

function MoverColumn({ title, icon, items, onSelect }: any) {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur flex items-center gap-2 sticky top-0">
                {icon}
                <h2 className="font-semibold text-slate-200">{title}</h2>
                <span className="ml-auto text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                    {items.length}
                </span>
            </div>

            <div className="divide-y divide-slate-800/50 overflow-y-auto max-h-[80vh]">
                {items.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 text-sm">No events yet</div>
                ) : (
                    items.map((item: any) => (
                        <div
                            key={item.symbol + item.event_time}
                            onClick={() => onSelect(item.symbol)}
                            className="p-4 hover:bg-slate-800/50 cursor-pointer transition-colors group"
                        >
                            <div className="flex justify-between items-start mb-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-slate-200 group-hover:text-blue-400 transition-colors">
                                        {item.symbol}
                                    </span>
                                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                        PERP
                                    </span>
                                </div>
                                <div className="text-right">
                                    {item.type === 'rise' ? (
                                        <div className="flex flex-col items-end">
                                            <span className={clsx("font-mono font-medium", item.change_pct_window >= 0 ? "text-emerald-400" : "text-rose-400")}>
                                                {item.change_pct_window > 0 ? '+' : ''}{item.change_pct_window?.toFixed(2)}%
                                            </span>
                                            <span className="text-[10px] text-slate-500">5m Chg</span>
                                        </div>
                                    ) : (
                                        <span className={clsx("font-mono font-medium", item.change_pct_24h >= 0 ? "text-emerald-400" : "text-rose-400")}>
                                            {item.change_pct_24h > 0 ? '+' : ''}{item.change_pct_24h?.toFixed(2)}%
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="flex justify-between items-center text-xs text-slate-500">
                                <span className={clsx(
                                    "px-1.5 py-0.5 rounded border",
                                    item.type === 'rise' ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-amber-500/20 bg-amber-500/10 text-amber-300"
                                )}>
                                    {item.status}
                                </span>
                                <span>
                                    {new Date(item.event_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
