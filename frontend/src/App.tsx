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
              {/* Brand */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#F0B90B" />
                    <path d="M2 17L12 22L22 17" stroke="#F0B90B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M2 12L12 17L22 12" stroke="#F0B90B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="brand-text">Trade Helper</span>
                </div>

                {/* Navigation */}
                <nav style={{ display: 'flex', gap: '4px', height: '100%' }}>
                  <NavLink
                    to="/movers"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none', padding: '0 12px', height: '48px', display: 'flex', alignItems: 'center', fontSize: '14px', fontWeight: 500 }}
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
