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
      background: 'var(--bg-primary)',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border-color)',
        background: 'var(--bg-secondary)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '0 24px',
          height: '56px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            {/* Logo */}
            <h1 className="logo">Trade Helper</h1>

            {/* Navigation */}
            <nav style={{
              display: 'flex',
              gap: '4px',
              background: 'var(--bg-tertiary)',
              padding: '4px',
              borderRadius: '10px'
            }}>
              <button
                onClick={() => setActiveTab('movers')}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 500,
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'all 0.15s ease',
                  background: activeTab === 'movers' ? 'var(--accent-blue-soft)' : 'transparent',
                  color: activeTab === 'movers' ? 'var(--accent-blue)' : 'var(--text-secondary)'
                }}
              >
                <TrendingUp size={16} />
                Top Movers
              </button>
              <button
                onClick={() => setActiveTab('chart')}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 500,
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'all 0.15s ease',
                  background: activeTab === 'chart' ? 'var(--accent-blue-soft)' : 'transparent',
                  color: activeTab === 'chart' ? 'var(--accent-blue)' : 'var(--text-secondary)'
                }}
              >
                <BarChart3 size={16} />
                Chart & Alerts
              </button>
            </nav>
          </div>

          {/* Active Symbol */}
          {activeTab === 'chart' && (
            <div style={{
              fontSize: '13px',
              color: 'var(--text-muted)',
              fontFamily: 'monospace',
              background: 'var(--bg-tertiary)',
              padding: '6px 12px',
              borderRadius: '6px'
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
        padding: '24px'
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
