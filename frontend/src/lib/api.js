import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("llmops_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const register = (name, email, password) =>
  api.post("/auth/register", { name, email, password });

export const login = async (email, password) => {
  const res = await api.post("/auth/login", { email, password });
  localStorage.setItem("llmops_token", res.data.access_token);
  return res.data;
};

export const logout = () => {
  localStorage.removeItem("llmops_token");
};

export const isLoggedIn = () => !!localStorage.getItem("llmops_token");

export const getProfile = () => api.get("/auth/me");

export const getAnalyticsSummary = (days = 30) =>
  api.get(`/analytics/summary?days=${days}`);

export const getCostForecast = () => api.get("/analytics/cost-forecast");

export const getRequestHistory = (page = 1) =>
  api.get(`/analytics/requests?page=${page}`);

export const getProviders = () => api.get("/providers/");

export const completeLLM = (payload) => api.post("/llm/complete", payload);

export const listApiKeys = () => api.get("/keys/");

export const addApiKey = (provider, keyName, apiKey, monthlyQuotaUsd = 50) =>
  api.post("/keys/", {
    provider,
    key_name: keyName,
    api_key: apiKey,
    monthly_quota_usd: monthlyQuotaUsd,
  });

export const deleteApiKey = (keyId) => api.delete(`/keys/${keyId}`);

export default api;
