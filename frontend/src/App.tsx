import { useState } from 'react';
import MoversPage from './pages/MoversPage';
import WatchlistPage from './pages/WatchlistPage';
import { TrendingUp, Bookmark } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'movers' | 'watchlist'>('movers');

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
                onClick={() => setActiveTab('watchlist')}
                className={`nav-tab ${activeTab === 'watchlist' ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  height: '100%'
                }}
              >
                <Bookmark size={16} />
                Watchlist
              </button>
            </nav>
          </div>
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
          <MoversPage onSymbolSelect={() => setActiveTab('watchlist')} />
        ) : (
          <WatchlistPage />
        )}
      </main>
    </div>
  );
}

export default App;
