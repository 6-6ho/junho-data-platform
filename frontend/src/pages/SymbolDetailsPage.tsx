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
        refetchInterval: 3600000
    });

    const { data: oi } = useQuery({
        queryKey: ['analysisOI', safeSymbol],
        queryFn: () => fetchAnalysisOI(safeSymbol),
        refetchInterval: 60000
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
        <div style={{ height: 'calc(100vh - 88px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div className="detail-header">
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

            <div style={{ display: 'flex', height: '480px', margin: 'var(--space-4)' }}>
                {/* Chart */}
                <div className="chart-area" style={{ flex: 1, borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                    <ChartWrapper symbol={safeSymbol} />
                </div>

                {/* Sidebar */}
                <div className="detail-sidebar">

                    {/* RS vs BTC */}
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

                    {/* RS vs Alts */}
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

                    {/* Listing Age */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <Clock size={14} />
                            <span>상장일</span>
                        </div>
                        <div className="stat-value">
                            {info ? `${info.days_since_listing}일` : '-'}
                        </div>
                        <div className="stat-sub">
                            {info?.listing_date || '-'} 상장
                        </div>
                    </div>

                    {/* Open Interest */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <DollarSign size={14} />
                            <span>미결제약정 (OI)</span>
                        </div>
                        <div style={{ height: '50px', marginBottom: 'var(--space-1)' }}>
                            {oi?.history && <OIMiniChart data={oi.history} />}
                        </div>
                        <div className="stat-value accent" style={{ fontSize: 'var(--text-base)' }}>
                            {oi ? formatKRW(oi.current_oi_value) : '-'}
                        </div>
                    </div>

                    {/* Market Cap */}
                    <div className="stat-card">
                        <div className="stat-label">
                            <BarChart3 size={14} />
                            <span>시가총액</span>
                        </div>
                        <div className="stat-value accent">
                            {info?.market_cap_usd != null ? formatKRW(info.market_cap_usd) : '-'}
                        </div>
                    </div>

                    {/* Unlocked Supply */}
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
                                    <div
                                        className="progress-fill"
                                        style={{ width: `${Math.min(info.unlock_percent, 100)}%` }}
                                    />
                                </div>
                                <div className="stat-sub">
                                    {info.circulating_supply?.toLocaleString()} / {info.total_supply?.toLocaleString()}
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
