import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAnalysisInfo, fetchTicker, fetchExchangeRate } from '../api/client';
import ChartWrapper from '../components/ChartWrapper';
import { ArrowLeft, Clock, Coins, Activity, BarChart3 } from 'lucide-react';

export default function SymbolDetailsPage() {
    const { symbol } = useParams<{ symbol: string }>();
    const navigate = useNavigate();
    const safeSymbol = symbol || 'BTCUSDT';

    const { data: info } = useQuery({
        queryKey: ['analysisInfo', safeSymbol],
        queryFn: () => fetchAnalysisInfo(safeSymbol),
        refetchInterval: 3600000
    });

    const { data: ticker } = useQuery({
        queryKey: ['ticker', safeSymbol],
        queryFn: () => fetchTicker(safeSymbol),
        refetchInterval: 2000
    });

    const { data: exchangeRate } = useQuery({
        queryKey: ['exchangeRate'],
        queryFn: fetchExchangeRate,
        staleTime: 3600000
    });

    const price = ticker ? parseFloat(ticker.lastPrice) : 0;
    const isUp = info?.price_change_percent >= 0;
    const krwRate = exchangeRate?.usd_krw || 1350;

    const formatKRW = (usd: number) => {
        const krw = usd * krwRate;
        if (krw >= 1_000_000_000_000) return `₩${(krw / 1_000_000_000_000).toFixed(1)}조`;
        if (krw >= 100_000_000) return `₩${(krw / 100_000_000).toFixed(1)}억`;
        if (krw >= 10_000) return `₩${(krw / 10_000).toFixed(0)}만`;
        return `₩${krw.toLocaleString()}`;
    };

    return (
        <div style={{ padding: 'var(--space-4)', height: 'calc(100vh - 88px)', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="detail-header" style={{ marginBottom: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
                <button onClick={() => navigate(-1)} className="back-btn">
                    <ArrowLeft size={18} />
                </button>
                <span className="detail-symbol">{safeSymbol.replace('USDT', '')}</span>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <span className="badge badge-perp">PERP</span>
                    {info?.has_spot_market && <span className="badge badge-spot">SPOT</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-3)', marginLeft: 'auto' }}>
                    <span className="detail-price">
                        ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                    </span>
                    {info && (
                        <span className={`detail-change ${isUp ? 'text-success' : 'text-danger'}`}>
                            {info.price_change_percent > 0 ? '+' : ''}{info.price_change_percent.toFixed(2)}%
                        </span>
                    )}
                </div>
            </div>

            {/* Content: Chart + 5 Stats */}
            <div style={{ display: 'flex', gap: 'var(--space-4)', flex: 1, minHeight: 0 }}>
                {/* Chart */}
                <div style={{ flex: 1, background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                    <ChartWrapper symbol={safeSymbol} />
                </div>

                {/* 5 Stat Cards */}
                <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>

                    {/* 1. RS vs BTC */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Activity size={14} />
                            <span>RS vs BTC</span>
                        </div>
                        <div className={`stat-value ${(info?.relative_strength_vs_btc >= 0) ? 'positive' : 'negative'}`}>
                            {info?.relative_strength_vs_btc != null
                                ? (info.relative_strength_vs_btc > 0 ? '+' : '') + info.relative_strength_vs_btc.toFixed(2) + '%'
                                : '-'}
                        </div>
                        <div className="stat-sub">
                            {safeSymbol.replace('USDT', '')}: {info?.price_change_percent?.toFixed(2)}% | BTC: {info?.btc_change_percent?.toFixed(2)}%
                        </div>
                    </div>

                    {/* 2. RS vs Alts */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Activity size={14} />
                            <span>RS vs Alts</span>
                        </div>
                        <div className={`stat-value ${(info?.relative_strength_vs_alts >= 0) ? 'positive' : 'negative'}`}>
                            {info?.relative_strength_vs_alts != null
                                ? (info.relative_strength_vs_alts > 0 ? '+' : '') + info.relative_strength_vs_alts.toFixed(2) + '%'
                                : '-'}
                        </div>
                        <div className="stat-sub">
                            Alts Avg: {info?.alts_avg_percent?.toFixed(2)}%
                        </div>
                    </div>

                    {/* 3. Listing Age */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Clock size={14} />
                            <span>상장일</span>
                        </div>
                        <div className="stat-value">
                            {info ? `${info.days_since_listing}일` : '-'}
                        </div>
                        <div className="stat-sub">
                            {info?.listing_date || '-'}
                        </div>
                    </div>

                    {/* 4. Market Cap */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <BarChart3 size={14} />
                            <span>시가총액</span>
                        </div>
                        <div className="stat-value accent">
                            {info?.market_cap_usd != null ? formatKRW(info.market_cap_usd) : '-'}
                        </div>
                    </div>

                    {/* 4.5 Open Interest & LS Ratio */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Activity size={14} />
                            <span>미체결약정 (OI)</span>
                        </div>
                        <div className="stat-value accent">
                            {info?.open_interest_usd != null ? formatKRW(info.open_interest_usd) : '-'}
                        </div>
                        {/* L/S Ratio Bar */}
                        {info?.long_short_ratio && (
                            <div style={{ marginTop: '8px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px', color: 'var(--text-secondary)' }}>
                                    <span style={{ color: '#26a69a' }}>L: {((info.long_short_ratio / (1 + info.long_short_ratio)) * 100).toFixed(0)}%</span>
                                    <span style={{ color: '#ef5350' }}>S: {(100 - (info.long_short_ratio / (1 + info.long_short_ratio)) * 100).toFixed(0)}%</span>
                                </div>
                                <div style={{ height: '4px', background: '#ef5350', borderRadius: '2px', overflow: 'hidden', display: 'flex' }}>
                                    <div style={{ width: `${(info.long_short_ratio / (1 + info.long_short_ratio)) * 100}%`, background: '#26a69a', height: '100%' }}></div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* 4.6 24h Volume */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <BarChart3 size={14} />
                            <span>24h 거래대금</span>
                        </div>
                        <div className="stat-value accent">
                            {info?.volume_24h_usd != null ? formatKRW(info.volume_24h_usd) : '-'}
                        </div>
                    </div>

                    {/* 5. Unlocked Supply */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Coins size={14} />
                            <span>유통량</span>
                        </div>
                        {info?.unlock_percent != null ? (
                            <>
                                <div className="stat-value accent">
                                    {info.unlock_percent.toFixed(1)}%
                                </div>
                                <div className="progress">
                                    <div className="progress-fill" style={{ width: `${Math.min(info.unlock_percent, 100)}%` }} />
                                </div>
                            </>
                        ) : (
                            <div className="stat-sub">데이터 없음</div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}

