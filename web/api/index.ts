import { QueryClient, type QueryClientConfig } from '@tanstack/react-query';
import { createApiClient } from './client';

export * from './client';
export * from '@tanstack/react-query';

export function createReactQueryClient(config?: QueryClientConfig) {
  return new QueryClient(config);
}


export const apiClient = createApiClient({
  baseUrl: 'http://127.0.0.1:9000',
  getAccessToken: () => localStorage.getItem('demo_token'),
  onUnauthorized: async () => {
    localStorage.removeItem('demo_token');
  },
});