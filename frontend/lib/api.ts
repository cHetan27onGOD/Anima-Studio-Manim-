import axios from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = Cookies.get('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  register: (data: any) => api.post('/api/auth/register', data),
  login: (data: URLSearchParams) => api.post('/api/auth/login', data),
  getMe: () => api.get('/api/auth/me'),
  health: () => api.get('/api/health'),
};

export const jobApi = {
  create: (prompt: string) => api.post('/api/jobs', { prompt }),
  list: () => api.get('/api/jobs'),
  get: (id: string) => api.get(`/api/jobs/${id}`),
  delete: (id: string) => api.delete(`/api/jobs/${id}`),
  updateCode: (id: string, code: string) => api.patch(`/api/jobs/${id}`, { code }),
  getLogs: (id: string) => `${API_URL}/api/jobs/${id}/logs/stream`,
  getVideo: (filename: string) => `${API_URL}/api/videos/${filename}`,
};

export default api;
