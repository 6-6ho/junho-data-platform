import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
    label: string;
    value: string;
    icon: LucideIcon;
    iconColor?: string; // Hex color or Tailwind class
    trend?: {
        label: string;
        isPositive: boolean;
    };
    tooltip?: string;
    subValue?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon: Icon, iconColor = "text-blue-400", trend, subValue }) => {
    // Tailwind color mapping helper
    const getBgColor = (colorClass: string) => {
        if (colorClass.includes('purple')) return 'bg-purple-500/10 border-purple-500/20';
        if (colorClass.includes('green')) return 'bg-green-500/10 border-green-500/20';
        if (colorClass.includes('red')) return 'bg-red-500/10 border-red-500/20';
        if (colorClass.includes('yellow')) return 'bg-yellow-500/10 border-yellow-500/20';
        return 'bg-blue-500/10 border-blue-500/20';
    };

    return (
        <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-700/50 rounded-xl p-5 flex flex-col justify-between h-full hover:border-zinc-500 transition-colors group">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2.5 rounded-lg border ${getBgColor(iconColor)}`}>
                    <Icon className={`w-6 h-6 ${iconColor}`} />
                </div>

                {trend && (
                    <div className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${trend.isPositive
                            ? 'bg-green-500/10 text-green-400 border-green-500/20'
                            : 'bg-red-500/10 text-red-400 border-red-500/20'
                        }`}>
                        {trend.label}
                    </div>
                )}
            </div>

            <div>
                <p className="text-zinc-400 text-sm font-medium mb-1">{label}</p>
                <h3 className="text-2xl font-bold text-white tracking-tight">{value}</h3>
                {subValue && <p className="text-zinc-500 text-xs mt-1">{subValue}</p>}
            </div>
        </div>
    );
};

export default StatCard;
