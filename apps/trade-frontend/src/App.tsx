import { BrowserRouter as Router, Routes, Route, Navigate, NavLink, useLocation, useParams } from 'react-router-dom';
import { ToastProvider } from './components/ToastContext';
import SymbolSearch from './components/SymbolSearch';
import MoversPage from './pages/MoversPage';
import SymbolDetailsPage from './pages/SymbolDetailsPage';
import SMCPage from './pages/SMCPage';
import PerformancePage from './pages/PerformancePage';
import ThemePage from './pages/ThemePage';
import DynamicThemePage from './pages/DynamicThemePage';
import MarketOverviewPage from './pages/MarketOverviewPage';
import StocksPage from './pages/StocksPage';

function LegacySymbolRedirect() {
  const { symbol } = useParams();
  return <Navigate to={`/crypto/symbol/${symbol}`} replace />;
}

function AppContent() {
  const location = useLocation();
  const path = location.pathname;

  const activeDomain = path.startsWith('/crypto') || path === '/'
    ? 'crypto'
    : path.startsWith('/stocks')
      ? 'stocks'
      : path.startsWith('/market')
        ? 'market'
        : 'crypto';

  return (
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
          <NavLink to="/market" className={() => `domain-tab ${activeDomain === 'market' ? 'active' : ''}`}>
            메인
          </NavLink>
          <NavLink to="/crypto/movers" className={() => `domain-tab ${activeDomain === 'crypto' ? 'active' : ''}`}>
            가상화폐
          </NavLink>
          <NavLink to="/stocks" className={() => `domain-tab ${activeDomain === 'stocks' ? 'active' : ''}`}>
            주식
          </NavLink>
        </nav>

        <SymbolSearch />
      </header>

      {/* Sub Nav - Crypto */}
      {activeDomain === 'crypto' && (
        <nav className="sub-nav">
          <NavLink to="/crypto/movers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Movers
          </NavLink>
          <NavLink to="/crypto/smc" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            SMC
          </NavLink>
          <NavLink to="/crypto/performance" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Performance
          </NavLink>
          <NavLink to="/crypto/theme" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Theme
          </NavLink>
          <NavLink to="/crypto/dynamic-theme" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Dynamic
          </NavLink>
        </nav>
      )}

      {/* Main Content */}
      <main style={{ flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '16px' }}>
        <Routes>
          {/* Default */}
          <Route path="/" element={<Navigate to="/crypto/movers" replace />} />

          {/* Market */}
          <Route path="/market" element={<MarketOverviewPage />} />

          {/* Crypto */}
          <Route path="/crypto/movers" element={<MoversPage />} />
          <Route path="/crypto/smc" element={<SMCPage />} />
          <Route path="/crypto/performance" element={<PerformancePage />} />
          <Route path="/crypto/theme" element={<ThemePage />} />
          <Route path="/crypto/dynamic-theme" element={<DynamicThemePage />} />
          <Route path="/crypto/symbol/:symbol" element={<SymbolDetailsPage />} />

          {/* Stocks */}
          <Route path="/stocks" element={<StocksPage />} />

          {/* Legacy redirects */}
          <Route path="/movers" element={<Navigate to="/crypto/movers" replace />} />
          <Route path="/smc" element={<Navigate to="/crypto/smc" replace />} />
          <Route path="/performance" element={<Navigate to="/crypto/performance" replace />} />
          <Route path="/theme" element={<Navigate to="/crypto/theme" replace />} />
          <Route path="/symbol/:symbol" element={<LegacySymbolRedirect />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <ToastProvider>
      <Router>
        <AppContent />
      </Router>
    </ToastProvider>
  );
}

export default App;
