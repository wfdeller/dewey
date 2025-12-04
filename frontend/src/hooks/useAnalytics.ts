import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { queryKeys } from '../services/queryClient';
import type {
  DashboardStats,
  SentimentTrend,
  CategoryBreakdown,
  VolumeData,
} from '../types';

interface AnalyticsParams {
  dateFrom?: string;
  dateTo?: string;
  categoryId?: string;
}

// Dashboard summary stats
export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.analytics.dashboard(),
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/analytics/dashboard');
      return data;
    },
    // Refresh every 5 minutes
    refetchInterval: 1000 * 60 * 5,
  });
}

// Sentiment trends over time
export function useSentimentTrends(params: AnalyticsParams = {}) {
  return useQuery({
    queryKey: queryKeys.analytics.sentiment(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value);
      });
      const { data } = await api.get<SentimentTrend[]>(
        `/analytics/sentiment?${searchParams.toString()}`
      );
      return data;
    },
  });
}

// Category breakdown
export function useCategoryBreakdown(params: AnalyticsParams = {}) {
  return useQuery({
    queryKey: queryKeys.analytics.categories(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value);
      });
      const { data } = await api.get<CategoryBreakdown[]>(
        `/analytics/categories?${searchParams.toString()}`
      );
      return data;
    },
  });
}

// Message volume over time
export function useMessageVolume(params: AnalyticsParams = {}) {
  return useQuery({
    queryKey: queryKeys.analytics.volume(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value);
      });
      const { data } = await api.get<VolumeData[]>(
        `/analytics/volume?${searchParams.toString()}`
      );
      return data;
    },
  });
}
