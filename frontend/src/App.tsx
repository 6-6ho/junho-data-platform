import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { ToastProvider } from './components/ToastContext';
import SymbolSearch from './components/SymbolSearch';
import MoversPage from './pages/MoversPage';
import SymbolDetailsPage from './pages/SymbolDetailsPage';

function App() {
  return (
    <ToastProvider>
      <Router>
        <div style={{
          minHeight: '100vh',
          background: 'var(--binance-bg-1)',
          color: 'var(--text-primary)',
          display: 'flex',
          flexDirection: 'column'
        }}>

          {/* Header */}
          <header style={{
            borderBottom: '1px solid var(--border-color)',
            background: 'rgba(10, 10, 15, 0.95)',
            backdropFilter: 'blur(12px)',
            position: 'sticky',
            top: 0,
            zIndex: 50
          }}>
            <div style={{
              maxWidth: '1400px',
              margin: '0 auto',
              padding: '0 20px',
              height: '56px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              {/* Brand */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: 'linear-gradient(135deg, #F0B90B 0%, #FF9F0A 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 0 20px rgba(240, 185, 11, 0.3)'
                  }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3 17L9 11L13 15L21 7" stroke="#0a0a0f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M17 7H21V11" stroke="#0a0a0f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <span className="brand-text">TradeHelper</span>
                </div>

                {/* Navigation */}
                <nav style={{ display: 'flex', gap: '4px', height: '100%' }}>
                  <NavLink
                    to="/movers"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none', padding: '0 16px', height: '56px', display: 'flex', alignItems: 'center', fontSize: '14px', fontWeight: 500 }}
                  >
                    Movers
                  </NavLink>
                </nav>
              </div>

              {/* Search */}
              <SymbolSearch />
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
            <Routes>
              <Route path="/" element={<Navigate to="/movers" replace />} />
              <Route path="/movers" element={<MoversPage />} />
              <Route path="/symbol/:symbol" element={<SymbolDetailsPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ToastProvider>
  );
}

export default App;
