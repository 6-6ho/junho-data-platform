import ChartWrapper from '../components/ChartWrapper';
import AlertsSidebar from '../components/AlertsSidebar';
import SymbolSearch from '../components/SymbolSearch';

interface ChartPageProps {
    symbol: string;
    onSymbolSelect: (symbol: string) => void;
}

export default function ChartPage({ symbol, onSymbolSelect }: ChartPageProps) {
    return (
        <div style={{
            height: 'calc(100vh - 80px)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
        }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0 4px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <h2 style={{
                        fontSize: '20px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        margin: 0
                    }}>
                        {symbol.replace('USDT', '')}
                        <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>/USDT</span>
                    </h2>
                    <span className="badge badge-perp">PERPETUAL</span>
                </div>
                <SymbolSearch currentSymbol={symbol} onSearch={onSymbolSelect} />
            </div>

            {/* Main Content */}
            <div style={{
                flex: 1,
                display: 'flex',
                gap: '12px',
                minHeight: 0
            }}>
                {/* Chart */}
                <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <ChartWrapper symbol={symbol} />
                </div>

                {/* Alerts Sidebar */}
                <div style={{ width: '280px', flexShrink: 0 }}>
                    <AlertsSidebar symbol={symbol} />
                </div>
            </div>
        </div>
    );
}
