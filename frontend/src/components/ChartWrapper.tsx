import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi, type CandlestickSeriesPartialOptions } from 'lightweight-charts';
import { useChartData } from '../hooks/useChartData';
import TrendlineOverlay from './TrendlineOverlay';
import { fetchTrendlines } from '../api/client';
import { useQuery } from '@tanstack/react-query';
import { Loader2, PenTool } from 'lucide-react';
import clsx from 'clsx';

interface Props {
    symbol: string;
}

export default function ChartWrapper({ symbol }: Props) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    const [isDrawing, setIsDrawing] = useState(false);
    const { data: chartData, isLoading } = useChartData(symbol);

    // Fetch Trendlines
    const { data: trendlines, refetch: refetchLines } = useQuery({
        queryKey: ['trendlines', symbol],
        queryFn: () => fetchTrendlines(symbol)
    });

    // Init Chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#0f172a' }, // Slate-900
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const candleSeries = (chart as any).addCandlestickSeries({
            upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350',
        } as CandlestickSeriesPartialOptions);

        chartRef.current = chart;
        seriesRef.current = candleSeries;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // Update Data
    useEffect(() => {
        if (seriesRef.current && chartData) {
            seriesRef.current.setData(chartData.candles);
            // Volume series could be added here similar to candleSeries
        }
    }, [chartData]);

    if (isLoading) return <div className="h-full flex items-center justify-center text-slate-500"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="relative w-full h-full flex flex-col">
            {/* Toolbar */}
            <div className="absolute top-4 left-4 z-20 flex gap-2">
                <button
                    onClick={() => setIsDrawing(!isDrawing)}
                    className={clsx(
                        "p-2 rounded shadow-lg border border-slate-700 transition-all",
                        isDrawing ? "bg-amber-500 text-white" : "bg-slate-800 text-slate-400 hover:text-slate-200"
                    )}
                    title="Draw Trendline"
                >
                    <PenTool size={20} />
                </button>
            </div>

            {/* Chart Container */}
            <div ref={chartContainerRef} className="flex-1 w-full h-full relative cursor-crosshair">
                {/* Helper SVG Overlay */}
                <TrendlineOverlay
                    chart={chartRef.current}
                    series={seriesRef.current}
                    symbol={symbol}
                    trendlines={trendlines || []}
                    onUpdate={refetchLines}
                    isDrawing={isDrawing}
                    onDrawingComplete={() => setIsDrawing(false)}
                />
            </div>
        </div>
    );
}
