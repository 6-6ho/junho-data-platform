import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';
import type { Time } from 'lightweight-charts';
import { useEffect, useRef, useState } from 'react';
import { fetchKlines, fetchSMCAnalysis } from '../api/client';
import { Loader2 } from 'lucide-react';

interface SMCChartProps {
    symbol: string;
    interval?: string;
}

export default function SMCChart({ symbol, interval = '1h' }: SMCChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const seriesRef = useRef<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [analysis, setAnalysis] = useState<any>(null);

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

        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#0ecb81',
            downColor: '#f6465d',
            borderVisible: false,
            wickUpColor: '#0ecb81',
            wickDownColor: '#f6465d',
        });

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

    useEffect(() => {
        const loadData = async () => {
            if (!symbol || !seriesRef.current) return;
            setIsLoading(true);
            try {
                // Fetch basic candle data first (500 candles roughly matches backend)
                const klines = await fetchKlines(symbol, interval, 500);

                // Format for chart
                const candles = klines.map((d: any) => ({
                    time: d[0] / 1000 as Time,
                    open: parseFloat(d[1]),
                    high: parseFloat(d[2]),
                    low: parseFloat(d[3]),
                    close: parseFloat(d[4]),
                }));

                seriesRef.current.setData(candles);

                // Fetch SMC Analysis
                const smcData = await fetchSMCAnalysis(symbol, interval);
                setAnalysis(smcData);

                // Add Markers for SMC features
                const markers: any[] = [];

                // 1. Swings (Market Structure)
                smcData.swings.forEach((swing: any) => {
                    // Only mark major swings to reduce clutter
                    markers.push({
                        time: new Date(swing.time).getTime() / 1000 as Time,
                        position: swing.type === 'high' ? 'aboveBar' : 'belowBar',
                        color: swing.type === 'high' ? '#f6465d' : '#0ecb81',
                        shape: swing.type === 'high' ? 'arrowDown' : 'arrowUp',
                        text: swing.type === 'high' ? 'H' : 'L',
                        size: 0.5
                    });
                });

                // 2. Order Blocks
                smcData.order_blocks.forEach((ob: any) => {
                    markers.push({
                        time: new Date(ob.time).getTime() / 1000 as Time,
                        position: ob.type === 'bullish' ? 'belowBar' : 'aboveBar',
                        color: ob.type === 'bullish' ? '#0ecb81' : '#f6465d',
                        shape: 'circle',
                        text: ob.type === 'bullish' ? 'OB Buy' : 'OB Sell',
                        size: 1
                    });
                });

                seriesRef.current.setMarkers(markers.sort((a, b) => (a.time as number) - (b.time as number)));

            } catch (error) {
                console.error("Failed to load SMC data", error);
            } finally {
                setIsLoading(false);
            }
        };

        loadData();
    }, [symbol, interval]);

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

            {/* Legend / Overlay Info */}
            <div style={{
                position: 'absolute', top: 10, left: 10, zIndex: 5,
                padding: '8px 12px', background: 'rgba(30, 35, 41, 0.8)',
                borderRadius: '4px', border: '1px solid #2b3139',
                color: '#eaecef', fontSize: '12px'
            }}>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{symbol} ({interval})</div>
                {analysis && (
                    <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: '#848e9c' }}>
                        <span>Trend: <span style={{ color: analysis.trend === 'bullish' ? '#0ecb81' : '#f6465d' }}>{analysis.trend.toUpperCase()}</span></span>
                        <span>•</span>
                        <span>OBs: {analysis.order_blocks.length}</span>
                        <span>•</span>
                        <span>FVGs: {analysis.fvgs.length}</span>
                    </div>
                )}
            </div>
        </div>
    );
}
