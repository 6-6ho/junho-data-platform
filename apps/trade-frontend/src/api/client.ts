import axios from 'axios';

const api = axios.create({
  baseURL: '/api', // Nginx proxy handles this
  timeout: 10000,
});

export const fetchMovers = async (limit = 20) => {
  const { data } = await api.get('/movers/latest', { params: { limit } });
  return data;
};

// Chart methods
export const fetchKlines = async (symbol: string, interval: string, limit = 1000) => {
  const { data } = await api.get('/klines', { params: { symbol, interval, limit } });
  return data;
};

// Favorites
export const fetchFavorites = async () => {
  const { data } = await api.get('/favorites');
  return data;
};

export const createFavoriteGroup = async (name: string) => {
  const { data } = await api.post('/favorites/groups', { name });
  return data;
};

export const deleteFavoriteGroup = async (groupId: string) => {
  const { data } = await api.delete(`/favorites/groups/${groupId}`);
  return data;
};

export const addFavoriteItem = async (groupId: string, symbol: string) => {
  const { data } = await api.post('/favorites/items', { group_id: groupId, symbol });
  return data;
};

export const deleteFavoriteItem = async (itemId: string) => {
  const { data } = await api.delete(`/favorites/items/${itemId}`);
  return data;
};

// Analysis
export const fetchAnalysisOI = async (symbol: string) => {
  const { data } = await api.get(`/analysis/oi/${symbol}`);
  return data;
};

export const fetchAnalysisInfo = async (symbol: string) => {
  const { data } = await api.get(`/analysis/info/${symbol}`);
  return data;
};

export const fetchMarketOverview = async () => {
  const { data } = await api.get('/analysis/market-overview');
  return data;
};

export const fetchExchangeRate = async () => {
  const { data } = await api.get('/analysis/exchange-rate');
  return data;
};

// Ticker (for Watchlist)
export const fetchTicker = async (symbol: string) => {
  const { data } = await api.get('/klines/ticker', { params: { symbol } });
  return data;
};


export const fetchSMCAnalysis = async (symbol: string, interval: string = '1h') => {
  const { data } = await api.get(`/smc/analysis/${symbol}`, { params: { interval } });
  return data;
};

// Analytics / Reports
export const fetchLatestReport = async (date?: string) => {
  const params = date ? { date } : {};
  const { data } = await api.get('/analytics/reports/latest', { params });
  return data;
};

export const fetchSystemPerformance = async () => {
  const { data } = await api.get('/system/performance');
  return data;
};
