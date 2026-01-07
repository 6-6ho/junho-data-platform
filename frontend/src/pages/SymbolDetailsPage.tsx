import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAnalysisInfo, fetchAnalysisOI, fetchTicker } from '../api/client';
import ChartWrapper from '../components/ChartWrapper';
import { ArrowLeft, Clock, TrendingUp, TrendingDown, Coins, Activity, DollarSign } from 'lucide-react';

export default function SymbolDetailsPage() {
    const { symbol } = useParams<{ symbol: string }>();
    const navigate = useNavigate();
    const safeSymbol = symbol || 'BTCUSDT';

    const { data: info } = useQuery({
        queryKey: ['analysisInfo', safeSymbol],
        queryFn: () => fetchAnalysisInfo(safeSymbol),
        staleTime: 60000
    });

    const { data: oi } = useQuery({
        queryKey: ['analysisOI', safeSymbol],
        queryFn: () => fetchAnalysisOI(safeSymbol),
        refetchInterval: 10000
    });

    const { data: ticker } = useQuery({
        queryKey: ['ticker', safeSymbol],
        queryFn: () => fetchTicker(safeSymbol),
        refetchInterval: 2000
    });

    const price = ticker ? parseFloat(ticker.lastPrice) : 0;
    const isUp = info?.price_change_percent >= 0;
    const relStrength = info?.relative_strength;

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
                <div style={{ width: '320px', background: 'var(--binance-bg-card)', overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

                    {/* 1. Relative Strength */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Activity size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Relative Strength (vs BTC)</span>
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: 600, color: (relStrength >= 0) ? 'var(--binance-green)' : 'var(--binance-red)' }}>
                            {relStrength ? (relStrength > 0 ? '+' : '') + relStrength.toFixed(2) + '%' : '-'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            {safeSymbol}: {info?.price_change_percent.toFixed(2)}% <br />
                            BTC: {info?.btc_change_percent.toFixed(2)}%
                        </div>
                    </div>

                    {/* 2. Listing Info */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Clock size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Listing Age</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 600 }}>
                            {info ? `${info.days_since_listing} Days` : '-'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            Listed: {info?.listing_date || '-'}
                        </div>
                    </div>

                    {/* 3. Open Interest */}
                    <div className="card" style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <DollarSign size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Open Interest</span>
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'monospace' }}>
                            {oi ? `${(oi.current_oi).toLocaleString()}` : '-'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            Value: {oi ? `$${(oi.current_oi_value / 1000000).toFixed(2)}M` : '-'}
                        </div>
                    </div>

                    {/* 4. Tokenomics (Placeholder) */}
                    <div className="card" style={{ padding: '16px', opacity: 0.7 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--text-tertiary)' }}>
                            <Coins size={16} />
                            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Unlocked Supply</span>
                        </div>
                        <div style={{ fontSize: '14px', color: 'var(--text-tertiary)' }}>
                            Data not available via API
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
