import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAnalysisInfo, fetchAnalysisOI, fetchTicker, fetchExchangeRate } from '../api/client';
import ChartWrapper from '../components/ChartWrapper';
import OIMiniChart from '../components/OIMiniChart';
import { ArrowLeft, Clock, Coins, Activity, DollarSign, BarChart3 } from 'lucide-react';

export default function SymbolDetailsPage() {
    const { symbol } = useParams<{ symbol: string }>();
    const navigate = useNavigate();
    const safeSymbol = symbol || 'BTCUSDT';

    const { data: info } = useQuery({
        queryKey: ['analysisInfo', safeSymbol],
        queryFn: () => fetchAnalysisInfo(safeSymbol),
        refetchInterval: 3600000 // 1 hour for market cap refresh
    });

    const { data: oi } = useQuery({
        queryKey: ['analysisOI', safeSymbol],
        queryFn: () => fetchAnalysisOI(safeSymbol),
        refetchInterval: 60000 // 1 min for OI refresh
    });

    const { data: ticker } = useQuery({
        queryKey: ['ticker', safeSymbol],
        queryFn: () => fetchTicker(safeSymbol),
        refetchInterval: 2000
    });

    const { data: exchangeRate } = useQuery({
        queryKey: ['exchangeRate'],
        queryFn: fetchExchangeRate,
        staleTime: 3600000 // 1 hour
    });

    const price = ticker ? parseFloat(ticker.lastPrice) : 0;
    const isUp = info?.price_change_percent >= 0;
    const krwRate = exchangeRate?.usd_krw || 1350;

    // Format KRW
    const formatKRW = (usd: number) => {
        const krw = usd * krwRate;
        if (krw >= 1_000_000_000_000) {
            return `₩${(krw / 1_000_000_000_000).toFixed(1)}조`;
        } else if (krw >= 100_000_000) {
            return `₩${(krw / 100_000_000).toFixed(1)}억`;
        } else if (krw >= 10_000) {
            return `₩${(krw / 10_000).toFixed(0)}만`;
        }
        return `₩${krw.toLocaleString()}`;
    };

    return (
        <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{
                padding: '16px 24px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                gap: '20px',
                background: 'var(--binance-bg-2)'
            }}>
                <button
                    onClick={() => navigate(-1)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}
                >
                    <ArrowLeft size={20} />
                </button>

                <h1 style={{ margin: 0, fontSize: '20px', color: 'var(--binance-yellow)' }}>{safeSymbol.replace('USDT', '')}</h1>

                <div style={{ display: 'flex', gap: '6px' }}>
                    <span style={{
                        padding: '2px 6px',
                        background: 'rgba(246, 70, 93, 0.2)',
                        color: '#f6465d',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 600
                    }}>PERP</span>
                    {info?.has_spot_market && (
                        <span style={{
                            padding: '2px 6px',
                            background: 'rgba(14, 203, 129, 0.2)',
                            color: '#0ecb81',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 600
                        }}>SPOT</span>
                    )}
                </div>

                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span style={{ fontSize: '24px', fontWeight: 600, fontFamily: 'monospace' }}>
                        ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    {info && (
                        <span style={{
                            color: isUp ? 'var(--binance-green)' : 'var(--binance-red)',
                            fontWeight: 500
                        }}>
                            {info.price_change_percent > 0 ? '+' : ''}{info.price_change_percent.toFixed(2)}%
                        </span>
                    )}
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Visuals (Chart) */}
                <div style={{ flex: 1, borderRight: '1px solid var(--border-color)', position: 'relative' }}>
                    <ChartWrapper symbol={safeSymbol} />
                </div>

                {/* Sidebar Info */}
                <div style={{ width: '320px', background: 'var(--binance-bg-card)', overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

                    {/* 1. Relative Strength vs BTC */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Activity size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>RS vs BTC</span>
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: 600, color: (info?.relative_strength_vs_btc >= 0) ? 'var(--binance-green)' : 'var(--binance-red)' }}>
                            {info?.relative_strength_vs_btc != null ? (info.relative_strength_vs_btc > 0 ? '+' : '') + info.relative_strength_vs_btc.toFixed(2) + '%' : '-'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            {safeSymbol}: {info?.price_change_percent?.toFixed(2)}% | BTC: {info?.btc_change_percent?.toFixed(2)}%
                        </div>
                    </div>

                    {/* 2. Relative Strength vs Alts Average */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Activity size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>RS vs Alts Avg</span>
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: 600, color: (info?.relative_strength_vs_alts >= 0) ? 'var(--binance-green)' : 'var(--binance-red)' }}>
                            {info?.relative_strength_vs_alts != null ? (info.relative_strength_vs_alts > 0 ? '+' : '') + info.relative_strength_vs_alts.toFixed(2) + '%' : '-'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            Alts Avg: {info?.alts_avg_percent?.toFixed(2)}% (15m cached)
                        </div>
                    </div>

                    {/* 3. Listing Info */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Clock size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Listing Age</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 600 }}>
                            {info ? `${info.days_since_listing} Days` : '-'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            Listed: {info?.listing_date || '-'}
                        </div>
                    </div>

                    {/* 4. Open Interest (1 min refresh, KRW) */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <DollarSign size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Open Interest</span>
                            <span style={{ fontSize: '9px', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>1분 갱신</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>
                            {oi ? `$${(oi.current_oi_value / 1_000_000).toFixed(2)}M` : '-'}
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--binance-yellow)', marginTop: '4px' }}>
                            {oi ? formatKRW(oi.current_oi_value) : '-'}
                        </div>
                        <div style={{ marginTop: '12px' }}>
                            {oi?.history && <OIMiniChart data={oi.history} />}
                        </div>
                    </div>

                    {/* 5. Market Cap (1 hour refresh, KRW) */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <BarChart3 size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Market Cap</span>
                            <span style={{ fontSize: '9px', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>1시간 갱신</span>
                        </div>
                        {info?.market_cap_usd != null ? (
                            <>
                                <div style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>
                                    ${(info.market_cap_usd / 1_000_000_000).toFixed(2)}B
                                </div>
                                <div style={{ fontSize: '13px', color: 'var(--binance-yellow)', marginTop: '4px' }}>
                                    {formatKRW(info.market_cap_usd)}
                                </div>
                            </>
                        ) : (
                            <div style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>
                                Data not available
                            </div>
                        )}
                    </div>

                    {/* 6. Unlocked Supply (CoinGecko) */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Coins size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Unlocked Supply</span>
                        </div>
                        {info?.unlock_percent != null ? (
                            <>
                                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                                    {info.unlock_percent.toFixed(1)}%
                                </div>
                                <div style={{
                                    marginTop: '8px',
                                    height: '6px',
                                    background: 'var(--binance-bg-3)',
                                    borderRadius: '3px',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{
                                        width: `${Math.min(info.unlock_percent, 100)}%`,
                                        height: '100%',
                                        background: 'var(--binance-yellow)'
                                    }} />
                                </div>
                                <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                                    {info.circulating_supply?.toLocaleString()} / {info.total_supply?.toLocaleString()}
                                </div>
                            </>
                        ) : (
                            <div style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>
                                Data not available
                            </div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}
