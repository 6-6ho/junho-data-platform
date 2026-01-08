import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { ToastProvider } from './components/ToastContext';
import SymbolSearch from './components/SymbolSearch';
import MoversPage from './pages/MoversPage';
import SymbolDetailsPage from './pages/SymbolDetailsPage';

function App() {
  return (
    <ToastProvider>
      <Router>
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

          {/* Header */}
          <header className="app-header">
            <div className="brand">
              <div className="brand-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M3 17L9 11L13 15L21 7" stroke="#050507" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M17 7H21V11" stroke="#050507" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span className="brand-text">TradeHelper</span>
            </div>

            <nav style={{ display: 'flex', gap: '4px' }}>
              <NavLink to="/movers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Movers
              </NavLink>
            </nav>

            <SymbolSearch />
          </header>

          {/* Main Content */}
          <main style={{ flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '16px' }}>
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
