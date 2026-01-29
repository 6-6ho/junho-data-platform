import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useEffect, useRef, useState } from 'react';
import { fetchKlines } from '../api/client';
import { Loader2 } from 'lucide-react';

interface ChartWrapperProps {
    symbol: string;
}

export default function ChartWrapper({ symbol }: ChartWrapperProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Initialize Chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#0b0e11' },
                textColor: '#848e9c',
            },
            grid: {
                vertLines: { color: '#1e2329' },
                horzLines: { color: '#1e2329' },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#2b3139',
            },
            rightPriceScale: {
                borderColor: '#2b3139',
            },
        });

        // Candlestick series
        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#0ecb81',
            downColor: '#f6465d',
            borderVisible: false,
            wickUpColor: '#0ecb81',
            wickDownColor: '#f6465d',
        });

        // Volume histogram series (styled to sit at bottom)
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: '', // Overlay on main pane
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.85, bottom: 0 }, // Push to bottom 15%
        });

        chartRef.current = chart;
        candleSeriesRef.current = candleSeries;
        volumeSeriesRef.current = volumeSeries;

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

    // Load Data
    useEffect(() => {
        const loadData = async () => {
            if (!symbol || !candleSeriesRef.current || !volumeSeriesRef.current) return;
            setIsLoading(true);
            try {
                // Fetch 1500 daily candles (max allowed by Binance in one request)
                const data = await fetchKlines(symbol, '1d', 1500);

                // Transform Binance [time, open, high, low, close, volume, ...] format
                const candles = data.map((d: any) => ({
                    time: d[0] / 1000,
                    open: parseFloat(d[1]),
                    high: parseFloat(d[2]),
                    low: parseFloat(d[3]),
                    close: parseFloat(d[4]),
                }));

                const volumes = data.map((d: any) => ({
                    time: d[0] / 1000,
                    value: parseFloat(d[5]), // volume field
                    color: parseFloat(d[4]) >= parseFloat(d[1]) ? 'rgba(14, 203, 129, 0.5)' : 'rgba(246, 70, 93, 0.5)',
                }));

                candleSeriesRef.current.setData(candles);
                volumeSeriesRef.current.setData(volumes);
            } catch (error) {
                console.error("Failed to load chart data", error);
            } finally {
                setIsLoading(false);
            }
        };

        loadData();
    }, [symbol]);

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            {isLoading && (
                <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'rgba(11, 14, 17, 0.7)', zIndex: 10
                }}>
                    <Loader2 className="animate-spin" size={32} color="var(--binance-yellow)" />
                </div>
            )}
            <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
        </div>
    );
}
