/**
 * Data Source Configuration
 * 
 * Feature flag to switch between mock data and live Supabase data.
 * Set VITE_DATA_SOURCE=supabase in .env to use real data.
 */

// Read from environment variable
const dataSource = (import.meta.env.VITE_DATA_SOURCE || 'mock') as 'mock' | 'supabase';

export const DATA_CONFIG = {
  source: dataSource,
  isMock: dataSource === 'mock',
  isLive: dataSource === 'supabase',
} as const;

export function getDataSource() {
  return DATA_CONFIG.source;
}

export function isUsingMockData() {
  return DATA_CONFIG.isMock;
}

export function isUsingLiveData() {
  return DATA_CONFIG.isLive;
}
