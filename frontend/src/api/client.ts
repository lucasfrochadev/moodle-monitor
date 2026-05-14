import axios from 'axios';
import { handleMockRequest } from '../mock/handler';

// Start in mock mode by default. Switch to real mode only if backend responds.
let mockMode = true;

(async () => {
  try {
    await axios.get('http://127.0.0.1:8000/api/health', { timeout: 3000 });
    mockMode = false;
  } catch {
    // stays in mock mode
  }
})();

export function setMockMode(enabled: boolean) {
  mockMode = enabled;
}

export function isMockMode() {
  return mockMode;
}

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Intercept all /api/* responses: on any failure, return mock data
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (mockMode || !error.response || error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED' || error.response?.status >= 400) {
      mockMode = true;
      const mockResponse = handleMockRequest(
        error.config?.method?.toUpperCase() || 'GET',
        error.config?.url || '',
        error.config?.data ? (() => { try { return JSON.parse(error.config.data); } catch { return undefined; } })() : undefined
      );
      if (mockResponse) {
        return Promise.resolve({
          data: mockResponse.data,
          status: 200,
          statusText: 'OK (mock)',
          headers: { 'content-type': 'application/json' },
          config: error.config,
        });
      }
    }

    const message = error.response?.data?.detail
      || error.response?.data?.message
      || error.message
      || 'Erro de conexão com o servidor';
    return Promise.reject(new Error(message));
  }
);

export default client;
