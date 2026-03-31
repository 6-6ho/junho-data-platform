import axios from 'axios';

const api = axios.create({
  baseURL: '/api/analytics',
  timeout: 10_000,
});

/* ===== Overview ===== */

/** { total_events, today_events, today_revenue, data_freshness_sec } */
export const fetchSummary = async () => {
  const { data } = await api.get('/summary');
  return data;
};

/** [{ time, [category]: number, ... }] — dynamic category keys */
export const fetchHourlyTraffic = async () => {
  const { data } = await api.get('/hourly-traffic');
  return data;
};

/** [{ hour, total_orders }] */
export const fetchHourlyThroughput = async () => {
  const { data } = await api.get('/hourly-throughput');
  return data;
};

/** { page_view, add_to_cart, purchase, conversion_rate } */
export const fetchFunnel = async () => {
  const { data } = await api.get('/funnel');
  return data;
};

/* ===== DQ ===== */

/** [{ date, completeness_score, validity_score, timeliness_score, total_score }] */
export const fetchDQScoreTrend = async () => {
  const { data } = await api.get('/dq/score-trend');
  return data;
};

/** [{ hour, category_total, payment_total, diff_pct }] */
export const fetchDQReconciliation = async () => {
  const { data } = await api.get('/dq/reconciliation');
  return data;
};

/** { total, breakdown } */
export const fetchDQAnomalyRawCount = async () => {
  const { data } = await api.get('/dq/anomaly-raw-count');
  return data;
};

/** [{ category, event_count, purchase_count, total_revenue }] */
export const fetchDQCategoryHealth = async () => {
  const { data } = await api.get('/dq/category-health');
  return data;
};

/** [{ dimension, rule_name, target, layer, trigger_count_7d, status }] */
export const fetchDQRulesSummary = async () => {
  const { data } = await api.get('/dq/rules-summary');
  return data;
};

/* ===== Mart ===== */

/** [{ date, category, revenue, orders, avg_value }] */
export const fetchMartDailySales = async (days = 7) => {
  const { data } = await api.get('/mart/daily-sales', { params: { days } });
  return data;
};

/** [{ segment, user_count }] */
export const fetchMartRFM = async () => {
  const { data } = await api.get('/mart/rfm-distribution');
  return data;
};

/** [{ antecedents, consequents, confidence, lift, support }] */
export const fetchMartAssociation = async (limit = 10) => {
  const { data } = await api.get('/mart/product-association', { params: { limit } });
  return data;
};

/** [{ week, revenue, orders }] */
export const fetchMartWeeklyTrend = async (weeks = 8) => {
  const { data } = await api.get('/mart/weekly-trend', { params: { weeks } });
  return data;
};
