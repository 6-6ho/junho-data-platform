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

// Network transfer speed
export const fetchNetworkInfo = async (symbol: string) => {
  const { data } = await api.get(`/analysis/networks/${symbol}`);
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
export const fetchAllSymbols = async () => {
  const { data } = await api.get('/analysis/symbols');
  return data;
};

export const fetchLatestReport = async (date?: string) => {
  const params = date ? { date } : {};
  const { data } = await api.get('/analytics/reports/latest', { params });
  return data;
};

// Screener
export const fetchScreenerOverview = async () => {
  const { data } = await api.get('/screener/overview');
  return data;
};

export const fetchScreenerCoins = async (params?: {
  exchange?: string;
  flag?: string;
  sort?: string;
}) => {
  const { data } = await api.get('/screener/coins', { params });
  return data;
};

// Listing
export const fetchRecentListings = async (params?: {
  limit?: number;
  exchange?: string;
}) => {
  const { data } = await api.get('/listing/recent', { params });
  return data;
};

export const fetchListingStats = async () => {
  const { data } = await api.get('/listing/stats');
  return data;
};

// Whale Monitor
export const fetchWhaleDashboard = async () => {
  const { data } = await api.get('/whale/dashboard');
  return data;
};

export const fetchWhaleEpisodes = async (params?: {
  limit?: number;
  label?: string;
  direction?: string;
}) => {
  const { data } = await api.get('/whale/episodes', { params });
  return data;
};

export const fetchWhaleActiveEpisodes = async () => {
  const { data } = await api.get('/whale/episodes/active');
  return data;
};

export const fetchWhaleEpisodeDetail = async (id: number) => {
  const { data } = await api.get(`/whale/episodes/${id}`);
  return data;
};

export const fetchWhaleStats = async () => {
  const { data } = await api.get('/whale/stats');
  return data;
};

// Auth
const authHeaders = () => {
  const token = localStorage.getItem('settings_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const login = async (password: string) => {
  const { data } = await api.post('/auth/login', { password });
  return data;
};

export const verifyAuth = async () => {
  const { data } = await api.get('/auth/verify', { headers: authHeaders() });
  return data;
};

// Watchlist (auth required)
export const fetchWatchlist = async () => {
  const { data } = await api.get('/settings/watchlist', { headers: authHeaders() });
  return data;
};

export const addWatchlistSymbol = async (symbol: string) => {
  const { data } = await api.post('/settings/watchlist', { symbol }, { headers: authHeaders() });
  return data;
};

export const removeWatchlistSymbol = async (symbol: string) => {
  const { data } = await api.delete(`/settings/watchlist/${symbol}`, { headers: authHeaders() });
  return data;
};

// Agent (auth required for mutations)
export const fetchAgentStats = async () => {
  const { data } = await api.get('/agent/stats');
  return data;
};

export const fetchAgentCriteria = async () => {
  const { data } = await api.get('/agent/criteria');
  return data;
};

export const fetchAgentRecentMemos = async (limit = 10) => {
  const { data } = await api.get('/agent/memos/recent', { params: { limit } });
  return data;
};

export const addAgentMemo = async (content: string, tags?: string[]) => {
  const { data } = await api.post('/agent/memo', { content, tags }, { headers: authHeaders() });
  return data;
};

export const searchAgentMemos = async (query: string, limit = 5) => {
  const { data } = await api.post('/agent/memo/search', { query, limit }, { headers: authHeaders() });
  return data;
};

export const screenCoins = async () => {
  const { data } = await api.post('/agent/screen', {}, { headers: authHeaders() });
  return data;
};

