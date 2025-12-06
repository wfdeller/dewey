import { api } from './api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Recommendation types
export type RecommendationStatus = 'active' | 'dismissed' | 'converted';
export type TriggerType = 'trending_topic' | 'sentiment_shift' | 'engagement_spike';

export interface CampaignRecommendation {
  id: string;
  tenant_id: string;
  trigger_type: TriggerType;
  category_id?: string;
  topic_keywords: string[];
  trend_data: TrendData;
  title: string;
  description: string;
  suggested_audience_size: number;
  suggested_filter: Record<string, unknown>;
  status: RecommendationStatus;
  converted_campaign_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TrendData {
  period: string;
  current_count: number;
  previous_count: number;
  change_percent: number;
  stance_breakdown?: Record<string, number>;
}

export interface RecommendationListResponse {
  items: CampaignRecommendation[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecommendationStatsResponse {
  total_active: number;
  total_dismissed: number;
  total_converted: number;
  by_trigger_type: Record<string, number>;
}

// API Service
export const recommendationService = {
  // List recommendations
  async listRecommendations(
    page = 1,
    page_size = 20,
    status?: RecommendationStatus,
    trigger_type?: TriggerType
  ): Promise<RecommendationListResponse> {
    const params: Record<string, unknown> = { page, page_size };
    if (status) params.status = status;
    if (trigger_type) params.trigger_type = trigger_type;
    const response = await api.get<RecommendationListResponse>('/campaign-recommendations', { params });
    return response.data;
  },

  // Get single recommendation
  async getRecommendation(id: string): Promise<CampaignRecommendation> {
    const response = await api.get<CampaignRecommendation>(`/campaign-recommendations/${id}`);
    return response.data;
  },

  // Dismiss recommendation
  async dismissRecommendation(id: string): Promise<CampaignRecommendation> {
    const response = await api.post<CampaignRecommendation>(`/campaign-recommendations/${id}/dismiss`);
    return response.data;
  },

  // Convert recommendation to campaign
  async convertRecommendation(
    id: string,
    campaign_name: string,
    template_id: string
  ): Promise<{ recommendation: CampaignRecommendation; campaign_id: string }> {
    const response = await api.post<{ recommendation: CampaignRecommendation; campaign_id: string }>(
      `/campaign-recommendations/${id}/convert`,
      { campaign_name, template_id }
    );
    return response.data;
  },

  // Get stats
  async getStats(): Promise<RecommendationStatsResponse> {
    const response = await api.get<RecommendationStatsResponse>('/campaign-recommendations/stats');
    return response.data;
  },
};

// React Query Hooks

export const useRecommendationsQuery = (
  page = 1,
  page_size = 20,
  status?: RecommendationStatus,
  trigger_type?: TriggerType
) => {
  return useQuery({
    queryKey: ['recommendations', page, page_size, status, trigger_type],
    queryFn: () => recommendationService.listRecommendations(page, page_size, status, trigger_type),
  });
};

export const useRecommendationQuery = (id: string) => {
  return useQuery({
    queryKey: ['recommendations', id],
    queryFn: () => recommendationService.getRecommendation(id),
    enabled: !!id,
  });
};

export const useRecommendationStatsQuery = () => {
  return useQuery({
    queryKey: ['recommendations', 'stats'],
    queryFn: () => recommendationService.getStats(),
  });
};

export const useDismissRecommendationMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => recommendationService.dismissRecommendation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
};

export const useConvertRecommendationMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      campaign_name,
      template_id,
    }: {
      id: string;
      campaign_name: string;
      template_id: string;
    }) => recommendationService.convertRecommendation(id, campaign_name, template_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
};
