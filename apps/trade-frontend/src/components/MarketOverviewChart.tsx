import { createChart, ColorType, LineSeries } from 'lightweight-charts';
import type { IChartApi, UTCTimestamp } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMarketOverview } from '../api/client';
import { TrendingUp, TrendingDown } from 'lucide-react';

export default function MarketOverviewChart() {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    const { data, isLoading } = useQuery({
        queryKey: ['marketOverview'],
        queryFn: fetchMarketOverview,
        refetchInterval: 60000, // 1 min refresh
        staleTime: 30000
    });

    useEffect(() => {
        if (!chartContainerRef.current || !data?.btc_returns) return;

        // Clean up existing chart
        if (chartRef.current) {
            chartRef.current.remove();
        }

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
            height: 200,
            rightPriceScale: {
                borderColor: '#2b3139',
            },
            timeScale: {
                borderColor: '#2b3139',
                timeVisible: true,
            },
        });

        // BTC Line
        const btcSeries = chart.addSeries(LineSeries, {
            color: '#f0b90b', // Binance Yellow
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: true,
            title: 'BTC',
        });

        const btcData = data.btc_returns.map((d: { time: number; value: number }) => ({
            time: (d.time / 1000) as UTCTimestamp,
            value: d.value
        }));
        btcSeries.setData(btcData);

        chart.timeScale().fitContent();
        chartRef.current = chart;

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
    }, [data]);

    const btcUp = data?.current_btc_24h >= 0;
    const altsUp = data?.current_alts_avg_24h >= 0;

    return (
        <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Market Overview (24h)
                </span>
                <div style={{ display: 'flex', gap: '16px', fontSize: '13px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {btcUp ? <TrendingUp size={14} style={{ color: 'var(--binance-green)' }} /> : <TrendingDown size={14} style={{ color: 'var(--binance-red)' }} />}
                        <span style={{ color: '#f0b90b', fontWeight: 600 }}>BTC</span>
                        <span style={{ color: btcUp ? 'var(--binance-green)' : 'var(--binance-red)', fontWeight: 500 }}>
                            {data?.current_btc_24h > 0 ? '+' : ''}{data?.current_btc_24h?.toFixed(2)}%
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {altsUp ? <TrendingUp size={14} style={{ color: 'var(--binance-green)' }} /> : <TrendingDown size={14} style={{ color: 'var(--binance-red)' }} />}
                        <span style={{ color: '#848e9c', fontWeight: 600 }}>Alts Avg</span>
                        <span style={{ color: altsUp ? 'var(--binance-green)' : 'var(--binance-red)', fontWeight: 500 }}>
                            {data?.current_alts_avg_24h > 0 ? '+' : ''}{data?.current_alts_avg_24h?.toFixed(2)}%
                        </span>
                        <span style={{ color: 'var(--text-tertiary)', fontSize: '11px' }}>({data?.alts_count} pairs)</span>
                    </div>
                </div>
            </div>

            {isLoading ? (
                <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>
                    Loading...
                </div>
            ) : (
                <div ref={chartContainerRef} style={{ width: '100%', height: '200px' }} />
            )}

            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '8px', textAlign: 'center' }}>
                BTC Daily Returns (Last 30 Days) — Yellow Line
            </div>
        </div>
    );
}
