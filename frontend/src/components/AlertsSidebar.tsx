import { fetchAlerts } from '../api/client';
import { useQuery } from '@tanstack/react-query';
import { BellRing } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';

export default function AlertsSidebar({ symbol }: { symbol: string }) {
    const { data: alerts } = useQuery({
        queryKey: ['alerts', symbol],
        queryFn: () => fetchAlerts(symbol),
        refetchInterval: 5000
    });

    return (
        <div className="w-80 border-l border-slate-800 bg-slate-900/50 flex flex-col">
            <div className="p-4 border-b border-slate-800 flex items-center gap-2 text-slate-200 font-semibold">
                <BellRing size={16} className="text-amber-400" />
                Alerts Feed
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {alerts && alerts.map((alert: any) => (
                    <div key={alert.event_time + alert.line_id} className="text-sm bg-slate-800/80 p-3 rounded border border-slate-700/50">
                        <div className="flex justify-between text-xs text-slate-500 mb-1">
                            <span>{formatDistanceToNow(new Date(alert.event_time))} ago</span>
                            <span className={clsx(
                                "uppercase font-bold",
                                alert.direction === 'break_up' ? "text-emerald-400" : "text-rose-400"
                            )}>
                                {alert.direction.replace('_', ' ')}
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-slate-300">Price: {alert.price}</span>
                            <span className="text-xs text-slate-600">Line: {alert.line_price.toFixed(2)}</span>
                        </div>
                    </div>
                ))}
                {(!alerts || alerts.length === 0) && (
                    <div className="text-center text-slate-600 text-sm mt-10">No alerts yet</div>
                )}
            </div>
        </div>
    );
}
