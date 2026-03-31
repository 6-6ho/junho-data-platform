import axios from 'axios';

const api = axios.create({
  baseURL: '/api/analytics',
  timeout: 10_000,
});

/* ===== Overview ===== */

export const fetchSummary = async () => {
  const { data } = await api.get('/summary');
  return data;
};

export const fetchHourlyTraffic = async () => {
  const { data } = await api.get('/hourly-traffic');
  return data;
};

export const fetchHourlyThroughput = async () => {
  const { data } = await api.get('/hourly-throughput');
  return data;
};

export const fetchFunnel = async () => {
  const { data } = await api.get('/funnel');
  return data;
};

/* ===== DQ ===== */

export const fetchDQScoreTrend = async () => {
  const { data } = await api.get('/dq/score-trend');
  return data;
};

export const fetchDQReconciliation = async () => {
  const { data } = await api.get('/dq/reconciliation');
  return data;
};

export const fetchDQAnomalyRawCount = async () => {
  const { data } = await api.get('/dq/anomaly-raw-count');
  return data;
};

export const fetchDQCategoryHealth = async () => {
  const { data } = await api.get('/dq/category-health');
  return data;
};

export const fetchDQRulesSummary = async () => {
  const { data } = await api.get('/dq/rules-summary');
  return data;
};

export const fetchDQAnomalies = async () => {
  const { data } = await api.get('/dq/anomalies');
  return data;
};

/* ===== Mart ===== */

export const fetchMartDailySales = async (days = 7) => {
  const { data } = await api.get('/mart/daily-sales', { params: { days } });
  return data;
};

export const fetchMartRFM = async () => {
  const { data } = await api.get('/mart/rfm-distribution');
  return data;
};

export const fetchMartAssociation = async (limit = 10) => {
  const { data } = await api.get('/mart/product-association', { params: { limit } });
  return data;
};

export const fetchMartWeeklyTrend = async (weeks = 8) => {
  const { data } = await api.get('/mart/weekly-trend', { params: { weeks } });
  return data;
};
