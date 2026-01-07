import axios from 'axios';

const api = axios.create({
  baseURL: '/api', // Nginx proxy handles this
  timeout: 10000,
});

export const fetchMovers = async (limit = 20) => {
  const { data } = await api.get('/movers/latest', { params: { limit } });
  return data;
};

export const fetchKlines = async (symbol: string, interval: string, limit = 1000) => {
  const { data } = await api.get('/klines', { params: { symbol, interval, limit } });
  return data;
};

export const fetchTrendlines = async (symbol: string) => {
  const { data } = await api.get('/trendlines', { params: { symbol } });
  return data;
};

export const createTrendline = async (trendline: any) => {
  const { data } = await api.post('/trendlines', trendline);
  return data;
};

export const updateTrendline = async (lineId: string, updates: any) => {
  const { data } = await api.put(`/trendlines/${lineId}`, updates);
  return data;
};

export const deleteTrendline = async (lineId: string) => {
  const { data } = await api.delete(`/trendlines/${lineId}`);
  return data;
};

export const fetchAlerts = async (symbol?: string, limit = 50) => {
  const { data } = await api.get('/alerts/latest', { params: { symbol, limit } });
  return data;
};
