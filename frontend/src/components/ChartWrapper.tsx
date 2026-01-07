import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi, type CandlestickSeriesPartialOptions } from 'lightweight-charts';
import { useChartData } from '../hooks/useChartData';
import TrendlineOverlay from './TrendlineOverlay';
import { fetchTrendlines } from '../api/client';
import { useQuery } from '@tanstack/react-query';
import { Loader2, PenTool } from 'lucide-react';

interface Props {
    symbol: string;
}

export default function ChartWrapper({ symbol }: Props) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    const [isDrawing, setIsDrawing] = useState(false);
    const { data: chartData, isLoading, error } = useChartData(symbol);

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
                background: { type: ColorType.Solid, color: '#0b0e11' }, // Binance dark
                textColor: '#848e9c',
            },
            grid: {
                vertLines: { color: '#1e2026' },
                horzLines: { color: '#1e2026' },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#2b2f36',
            },
            rightPriceScale: {
                borderColor: '#2b2f36',
            },
            crosshair: {
                vertLine: {
                    color: '#848e9c',
                    width: 1,
                    style: 3,
                    labelBackgroundColor: '#1e2026',
                },
                horzLine: {
                    color: '#848e9c',
                    width: 1,
                    style: 3,
                    labelBackgroundColor: '#1e2026',
                },
            },
        });

        const candleSeries = (chart as any).addCandlestickSeries({
            upColor: '#0ecb81',      // Binance green
            downColor: '#f6465d',    // Binance red
            borderVisible: false,
            wickUpColor: '#0ecb81',
            wickDownColor: '#f6465d',
        } as CandlestickSeriesPartialOptions);

        chartRef.current = chart;
        seriesRef.current = candleSeries;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                    height: chartContainerRef.current.clientHeight
                });
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
        }
    }, [chartData]);

    if (isLoading) {
        return (
            <div style={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-tertiary)'
            }}>
                <Loader2 className="loading" size={24} />
            </div>
        );
    }

    if (error) {
        return (
            <div style={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--binance-red)',
                flexDirection: 'column',
                gap: '8px'
            }}>
                <span>Failed to load chart data</span>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                    Check if the API is running
                </span>
            </div>
        );
    }

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Toolbar */}
            <div style={{
                position: 'absolute',
                top: '12px',
                left: '12px',
                zIndex: 20,
                display: 'flex',
                gap: '8px'
            }}>
                <button
                    onClick={() => setIsDrawing(!isDrawing)}
                    style={{
                        padding: '8px',
                        borderRadius: '4px',
                        border: '1px solid var(--border-color)',
                        background: isDrawing ? 'var(--binance-yellow)' : 'var(--binance-bg-3)',
                        color: isDrawing ? '#0b0e11' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.15s ease'
                    }}
                    title="Draw Trendline"
                >
                    <PenTool size={18} />
                </button>
            </div>

            {/* Chart Container */}
            <div
                ref={chartContainerRef}
                style={{
                    flex: 1,
                    width: '100%',
                    height: '100%',
                    cursor: isDrawing ? 'crosshair' : 'default'
                }}
            >
                {/* Trendline Overlay */}
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
