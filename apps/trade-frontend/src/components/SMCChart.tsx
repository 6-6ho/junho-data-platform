import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';
import type { Time } from 'lightweight-charts';
import { useEffect, useRef, useState } from 'react';
import { fetchKlines, fetchSMCAnalysis } from '../api/client';
import { Loader2 } from 'lucide-react';

interface SMCChartProps {
    symbol: string;
    interval?: string;
}


export default function SMCChart({ symbol, interval = '4h' }: SMCChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const seriesRef = useRef<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [analysis, setAnalysis] = useState<any>(null);
    const [overlayBoxes, setOverlayBoxes] = useState<any[]>([]);

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

        // --- Overlay Logic ---
        const updateOverlay = () => {
            if (!chart || !candleSeries || !analysis) return;

            const newBoxes: any[] = [];
            const timeScale = chart.timeScale();

            // Get visible range to avoid rendering off-screen (optional optimization)
            // const visibleRange = timeScale.getVisibleLogicalRange();

            analysis.order_blocks.forEach((ob: any) => {
                const startTime = ob.time / 1000 as Time;

                // Calculate X coordinates
                // Note: timeToCoordinate returns X relative to chart width
                const x1 = timeScale.timeToCoordinate(startTime);

                // For OBs, we usually extend to the right (current time or "future")
                // We'll approximate "end" as the rightmost edge of the chart for now, or X+200px
                // A better approach is to extend to the latest bar.

                if (x1 === null) return; // Time not on scale? (Shouldn't happen if data loaded)

                // y coordinates
                const y1 = candleSeries.priceToCoordinate(ob.top);
                const y2 = candleSeries.priceToCoordinate(ob.bottom);

                if (y1 === null || y2 === null) return;

                newBoxes.push({
                    x: x1,
                    y: Math.min(y1, y2),
                    width: 500, // Fixed width extension for now (visual indicator)
                    height: Math.abs(y1 - y2),
                    color: ob.type === 'bullish' ? 'rgba(14, 203, 129, 0.2)' : 'rgba(246, 70, 93, 0.2)',
                    borderColor: ob.type === 'bullish' ? '#0ecb81' : '#f6465d',
                    type: ob.type
                });
            });
            setOverlayBoxes(newBoxes);
        };

        // Subscribe to changes to update overlay positions
        chart.timeScale().subscribeVisibleTimeRangeChange(updateOverlay);
        // Also update when data is set (handled in loadData via effect dependency)
        // Check if we need to hook into logical range changes for scrolling

        window.addEventListener('resize', handleResize);

        // Expose updateOverlay to the outer scope or ref for when data loads? 
        // We'll use a specific useEffect for data loading that sets analysis state, 
        // triggering a re-render or effect that calls updateOverlay.

        // Actually, we can't easily subscribe `updateOverlay` if it depends on `analysis` state which changes.
        // We will attach the subscriber inside the effect that depends on `analysis`.

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
            seriesRef.current = null;
            chartRef.current = null;
        };
    }, []); // Run once for setup

    // Effect to handle data loading and updating series
    useEffect(() => {
        const loadData = async () => {
            if (!symbol || !seriesRef.current) return;
            setIsLoading(true);
            try {
                const klines = await fetchKlines(symbol, interval, 500);

                const candles = klines.map((d: any) => ({
                    time: d[0] / 1000 as Time,
                    open: parseFloat(d[1]),
                    high: parseFloat(d[2]),
                    low: parseFloat(d[3]),
                    close: parseFloat(d[4]),
                }));

                seriesRef.current.setData(candles);

                const smcData = await fetchSMCAnalysis(symbol, interval);
                setAnalysis(smcData); // This triggers the overlay effect

                // Add Markers (Swings only)
                const markers: any[] = [];
                smcData.swings.forEach((swing: any) => {
                    markers.push({
                        time: swing.time / 1000 as Time,
                        position: swing.type === 'high' ? 'aboveBar' : 'belowBar',
                        color: swing.type === 'high' ? '#f6465d' : '#0ecb81',
                        shape: swing.type === 'high' ? 'arrowDown' : 'arrowUp',
                        text: swing.type === 'high' ? 'H' : 'L',
                        size: 1
                    });
                });
                seriesRef.current.setMarkers(markers.sort((a: any, b: any) => (a.time as number) - (b.time as number)));

            } catch (error) {
                console.error("Failed to load SMC data", error);
            } finally {
                setIsLoading(false);
            }
        };
        loadData();
    }, [symbol, interval]);

    // Effect to sync overlay with analysis and scrolling
    useEffect(() => {
        if (!analysis || !chartRef.current || !seriesRef.current) return;

        const updateOverlay = () => {
            const chart = chartRef.current;
            const series = seriesRef.current;
            const timeScale = chart.timeScale();
            const newBoxes: any[] = [];

            analysis.order_blocks.forEach((ob: any) => {
                const startTime = ob.time / 1000 as Time;
                const x1 = timeScale.timeToCoordinate(startTime);

                // If x1 is null, it might be out of range, but we still want to draw if it extends into view?
                // For simplicity, skip if null.
                if (x1 === null) return;

                const y1 = series.priceToCoordinate(ob.top);
                const y2 = series.priceToCoordinate(ob.bottom);

                if (y1 === null || y2 === null) return;

                // Extend to the right edge of chart area
                // We'll calculate width dynamically: Chart Width - x1
                // Or slightly less.
                const chartWidth = chartContainerRef.current?.clientWidth || 800;
                const width = Math.max(50, chartWidth - x1);

                newBoxes.push({
                    x: x1,
                    y: Math.min(y1, y2),
                    width: width,
                    height: Math.abs(y1 - y2),
                    color: ob.type === 'bullish' ? 'rgba(14, 203, 129, 0.25)' : 'rgba(246, 70, 93, 0.25)',
                    borderColor: ob.type === 'bullish' ? '#0ecb81' : '#f6465d',
                    type: ob.type
                });
            });
            setOverlayBoxes(newBoxes);
        };

        // Initial update
        // We need a small delay for chart to fully render data coords
        setTimeout(updateOverlay, 100);

        const timeScale = chartRef.current.timeScale();
        timeScale.subscribeVisibleTimeRangeChange(updateOverlay);
        timeScale.subscribeVisibleLogicalRangeChange(updateOverlay); // Safer

        return () => {
            timeScale.unsubscribeVisibleTimeRangeChange(updateOverlay);
            timeScale.unsubscribeVisibleLogicalRangeChange(updateOverlay);
        };
    }, [analysis]);

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

            {/* Chart Container */}
            <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />

            {/* Overlay Layer for OB Zones */}
            <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                pointerEvents: 'none', overflow: 'hidden', zIndex: 2
            }}>
                {overlayBoxes.map((box, i) => (
                    <div key={i} style={{
                        position: 'absolute',
                        left: box.x,
                        top: box.y,
                        width: box.width,
                        height: box.height,
                        backgroundColor: box.color,
                        border: `1px solid ${box.borderColor}`,
                        opacity: 0.8 // Additional opacity tweak
                    }} />
                ))}
            </div>

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
