import { useState } from 'react';
import MoversPage from './pages/MoversPage';
import ChartPage from './pages/ChartPage';
import { TrendingUp, BarChart3 } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'movers' | 'chart'>('movers');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol);
    setActiveTab('chart');
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--binance-bg-1)',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header - Binance style */}
      <header style={{
        borderBottom: '1px solid var(--border-color)',
        background: 'var(--binance-bg-2)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '0 16px',
          height: '48px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            {/* Logo */}
            <h1 className="logo">Trade Helper</h1>

            {/* Navigation - Binance tab style */}
            <nav style={{
              display: 'flex',
              gap: '0',
              height: '48px',
              alignItems: 'center'
            }}>
              <button
                onClick={() => setActiveTab('movers')}
                className={`nav-tab ${activeTab === 'movers' ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  height: '100%'
                }}
              >
                <TrendingUp size={16} />
                Top Movers
              </button>
              <button
                onClick={() => setActiveTab('chart')}
                className={`nav-tab ${activeTab === 'chart' ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  height: '100%'
                }}
              >
                <BarChart3 size={16} />
                Chart
              </button>
            </nav>
          </div>

          {/* Active Symbol Badge */}
          {activeTab === 'chart' && (
            <div style={{
              fontSize: '12px',
              color: 'var(--binance-yellow)',
              fontFamily: 'monospace',
              background: 'rgba(240, 185, 11, 0.1)',
              padding: '4px 12px',
              borderRadius: '2px',
              fontWeight: 500
            }}>
              {selectedSymbol}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main style={{
        flex: 1,
        maxWidth: '1400px',
        margin: '0 auto',
        width: '100%',
        padding: '16px'
      }}>
        {activeTab === 'movers' ? (
          <MoversPage onSymbolSelect={handleSymbolSelect} />
        ) : (
          <ChartPage symbol={selectedSymbol} onSymbolSelect={handleSymbolSelect} />
        )}
      </main>
    </div>
  );
}

export default App;
