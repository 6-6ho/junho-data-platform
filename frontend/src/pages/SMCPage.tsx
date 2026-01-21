import { useState } from 'react';
import SMCChart from '../components/SMCChart';

export default function SMCPage() {
    const [interval, setInterval] = useState('1h');

    return (
        <div style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 8px' }}>
                <h1 style={{ fontSize: '20px', fontWeight: 'bold', color: '#eaecef', margin: 0 }}>Smart Money Concepts (SMC)</h1>

                <div style={{ display: 'flex', gap: '8px', background: '#1e2329', padding: '4px', borderRadius: '4px' }}>
                    {['15m', '1h', '4h'].map(tf => (
                        <button
                            key={tf}
                            onClick={() => setInterval(tf)}
                            style={{
                                background: interval === tf ? '#2b3139' : 'transparent',
                                color: interval === tf ? '#f0b90b' : '#848e9c',
                                border: 'none',
                                padding: '4px 12px',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '13px',
                                fontWeight: 500
                            }}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            {/* Charts Grid */}
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', minHeight: 0 }}>
                {/* BTC Container */}
                <div style={{ background: '#1e2329', borderRadius: '8px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '8px 12px', borderBottom: '1px solid #2b3139', fontSize: '14px', fontWeight: 'bold', color: '#f0b90b' }}>
                        Bitcoin (BTC)
                    </div>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <SMCChart symbol="BTCUSDT" interval={interval} />
                    </div>
                </div>

                {/* ETH Container */}
                <div style={{ background: '#1e2329', borderRadius: '8px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '8px 12px', borderBottom: '1px solid #2b3139', fontSize: '14px', fontWeight: 'bold', color: '#627eea' }}>
                        Ethereum (ETH)
                    </div>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <SMCChart symbol="ETHUSDT" interval={interval} />
                    </div>
                </div>
            </div>
        </div>
    );
}
