import { createChart, ColorType, LineSeries } from 'lightweight-charts';
import type { IChartApi, UTCTimestamp } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

interface OIMiniChartProps {
    data: { timestamp: number; sumOpenInterestValue: string }[];
}

export default function OIMiniChart({ data }: OIMiniChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        // Clear existing chart
        if (chartRef.current) {
            chartRef.current.remove();
        }

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#848e9c',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { visible: false },
            },
            width: chartContainerRef.current.clientWidth,
            height: 60,
            rightPriceScale: { visible: false },
            leftPriceScale: { visible: false },
            timeScale: { visible: false },
            crosshair: { mode: 0 }, // Hidden crosshair
            handleScale: false,
            handleScroll: false,
        });

        const series = chart.addSeries(LineSeries, {
            color: '#f0b90b',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        const chartData = data.map((d) => ({
            time: (d.timestamp / 1000) as UTCTimestamp,
            value: parseFloat(d.sumOpenInterestValue) / 1000000, // Convert to millions
        }));

        series.setData(chartData);
        chart.timeScale().fitContent();
        chartRef.current = chart;

        return () => {
            chart.remove();
        };
    }, [data]);

    if (!data || data.length === 0) {
        return <div style={{ color: 'var(--text-tertiary)', fontSize: '12px' }}>No OI history</div>;
    }

    return <div ref={chartContainerRef} style={{ width: '100%', height: '60px' }} />;
}
