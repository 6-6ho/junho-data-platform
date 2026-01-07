import { useState } from 'react';
import MoversPage from './pages/MoversPage';
import ChartPage from './pages/ChartPage';
import { Activity, BarChart2 } from 'lucide-react';
import clsx from 'clsx';

function App() {
  const [activeTab, setActiveTab] = useState<'movers' | 'chart'>('movers');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol);
    setActiveTab('chart');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header / Nav */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              TradeHelper
            </h1>

            <nav className="flex gap-1 bg-slate-800/50 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab('movers')}
                className={clsx(
                  "px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
                  activeTab === 'movers'
                    ? "bg-slate-700 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                )}
              >
                <Activity size={16} />
                Top Movers
              </button>
              <button
                onClick={() => setActiveTab('chart')}
                className={clsx(
                  "px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
                  activeTab === 'chart'
                    ? "bg-slate-700 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                )}
              >
                <BarChart2 size={16} />
                Chart & Alerts
              </button>
            </nav>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            {activeTab === 'chart' && `Active: ${selectedSymbol}`}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4">
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
