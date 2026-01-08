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
        <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div className="detail-header">
                <button onClick={() => navigate(-1)} className="detail-back-btn">
                    <ArrowLeft size={18} />
                </button>

                <h1 className="detail-symbol">{safeSymbol.replace('USDT', '')}</h1>

                <div style={{ display: 'flex', gap: '6px' }}>
                    <span className="badge-perp">PERP</span>
                    {info?.has_spot_market && <span className="badge-success">SPOT</span>}
                </div>

                <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginLeft: '8px' }}>
                    <span className="detail-price">
                        ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    {info && (
                        <span className={`detail-change ${isUp ? 'pct-up' : 'pct-down'}`}>
                            {info.price_change_percent > 0 ? '+' : ''}{info.price_change_percent.toFixed(2)}%
                        </span>
                    )}
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Chart */}
                <div className="chart-container">
                    <ChartWrapper symbol={safeSymbol} />
                </div>

                {/* Sidebar */}
                <div className="detail-sidebar">

                    {/* RS vs BTC */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <Activity size={16} />
                            <span className="stat-card-title">RS vs BTC</span>
                        </div>
                        <div className={`stat-card-value ${(info?.relative_strength_vs_btc >= 0) ? 'positive' : 'negative'}`}>
                            {info?.relative_strength_vs_btc != null
                                ? (info.relative_strength_vs_btc > 0 ? '+' : '') + info.relative_strength_vs_btc.toFixed(2) + '%'
                                : '-'}
                        </div>
                        <div className="stat-card-sub">
                            {safeSymbol}: {info?.price_change_percent?.toFixed(2)}% | BTC: {info?.btc_change_percent?.toFixed(2)}%
                        </div>
                    </div>

                    {/* RS vs Alts */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <Activity size={16} />
                            <span className="stat-card-title">RS vs Alts Avg</span>
                        </div>
                        <div className={`stat-card-value ${(info?.relative_strength_vs_alts >= 0) ? 'positive' : 'negative'}`}>
                            {info?.relative_strength_vs_alts != null
                                ? (info.relative_strength_vs_alts > 0 ? '+' : '') + info.relative_strength_vs_alts.toFixed(2) + '%'
                                : '-'}
                        </div>
                        <div className="stat-card-sub">
                            Alts Avg: {info?.alts_avg_percent?.toFixed(2)}%
                        </div>
                    </div>

                    {/* Listing Age */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <Clock size={16} />
                            <span className="stat-card-title">상장일</span>
                        </div>
                        <div className="stat-card-value">
                            {info ? `${info.days_since_listing}일` : '-'}
                        </div>
                        <div className="stat-card-sub">
                            {info?.listing_date || '-'} 상장
                        </div>
                    </div>

                    {/* Open Interest */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <DollarSign size={16} />
                            <span className="stat-card-title">OI 추이</span>
                        </div>
                        <div style={{ height: '70px', marginBottom: '8px' }}>
                            {oi?.history && <OIMiniChart data={oi.history} />}
                        </div>
                        <div className="stat-card-value gold" style={{ fontSize: '16px' }}>
                            {oi ? formatKRW(oi.current_oi_value) : '-'}
                        </div>
                    </div>

                    {/* Market Cap */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <BarChart3 size={16} />
                            <span className="stat-card-title">시가총액</span>
                        </div>
                        <div className="stat-card-value gold">
                            {info?.market_cap_usd != null ? formatKRW(info.market_cap_usd) : '-'}
                        </div>
                    </div>

                    {/* Unlocked Supply */}
                    <div className="stat-card">
                        <div className="stat-card-header">
                            <Coins size={16} />
                            <span className="stat-card-title">유통량</span>
                        </div>
                        {info?.unlock_percent != null ? (
                            <>
                                <div className="stat-card-value gold">
                                    {info.unlock_percent.toFixed(1)}%
                                </div>
                                <div className="progress-bar" style={{ marginTop: '10px' }}>
                                    <div
                                        className="progress-bar-fill"
                                        style={{ width: `${Math.min(info.unlock_percent, 100)}%` }}
                                    />
                                </div>
                                <div className="stat-card-sub">
                                    {info.circulating_supply?.toLocaleString()} / {info.total_supply?.toLocaleString()}
                                </div>
                            </>
                        ) : (
                            <div className="stat-card-sub">데이터 없음</div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}
