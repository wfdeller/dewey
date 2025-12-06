import { api } from './api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Campaign types
export type CampaignStatus = 'draft' | 'scheduled' | 'active' | 'paused' | 'completed' | 'cancelled';
export type CampaignType = 'standard' | 'ab_test' | 'automated';
export type RecipientStatus = 'pending' | 'queued' | 'sent' | 'delivered' | 'opened' | 'clicked' | 'bounced' | 'failed' | 'unsubscribed';

// Campaign interface
export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  campaign_type: CampaignType;
  template_id: string;
  variant_b_template_id?: string;
  ab_test_split: number;
  status: CampaignStatus;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  total_recipients: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_unsubscribed: number;
  unique_opens: number;
  unique_clicks: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignDetail extends Campaign {
  recipient_filter: RecipientFilter;
  send_rate_per_hour?: number;
  from_email_override?: string;
  from_name_override?: string;
  reply_to_override?: string;
  paused_at?: string;
  ab_test_winner_metric?: string;
  ab_test_winning_variant?: string;
  created_by_id?: string;
  job_id?: string;
}

export interface RecipientFilter {
  mode?: 'filter' | 'manual';
  tags?: string[];
  tag_match?: 'any' | 'all';
  categories?: Array<{ id: string; stance?: string }>;
  category_match?: 'any' | 'all';
  custom_fields?: Array<{ field_id: string; operator: string; value: string }>;
  states?: string[];
  zip_codes?: string[];
  party_affiliations?: string[];
  has_email?: boolean;
  exclude_suppressed?: boolean;
  manual_contact_ids?: string[];
}

export interface CampaignCreate {
  name: string;
  description?: string;
  campaign_type?: CampaignType;
  template_id: string;
  variant_b_template_id?: string;
  ab_test_split?: number;
  recipient_filter?: RecipientFilter;
  send_rate_per_hour?: number;
  from_email_override?: string;
  from_name_override?: string;
  reply_to_override?: string;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  template_id?: string;
  variant_b_template_id?: string;
  ab_test_split?: number;
  recipient_filter?: RecipientFilter;
  scheduled_at?: string;
  send_rate_per_hour?: number;
  from_email_override?: string;
  from_name_override?: string;
  reply_to_override?: string;
}

export interface CampaignRecipient {
  id: string;
  campaign_id: string;
  contact_id: string;
  email: string;
  variant?: string;
  status: RecipientStatus;
  sent_at?: string;
  opened_at?: string;
  clicked_at?: string;
  bounced_at?: string;
  open_count: number;
  click_count: number;
  error_message?: string;
}

export interface CampaignAnalytics {
  campaign_id: string;
  status: CampaignStatus;
  total_recipients: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_unsubscribed: number;
  total_failed: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  unsubscribe_rate: number;
  unique_opens: number;
  unique_clicks: number;
  unique_open_rate: number;
  unique_click_rate: number;
  ab_test_results?: Record<string, unknown>;
  timeline?: Array<Record<string, unknown>>;
}

export interface RecipientFilterPreview {
  total_count: number;
  sample_contacts: Array<Record<string, unknown>>;
}

// Response types
export interface CampaignListResponse {
  items: Campaign[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CampaignRecipientsResponse {
  items: CampaignRecipient[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CampaignStatsResponse {
  total_campaigns: number;
  by_status: Record<string, number>;
  total_sent: number;
  total_opened: number;
  total_clicked: number;
}

// API Service
export const campaignService = {
  // List campaigns with filters
  async listCampaigns(
    page = 1,
    page_size = 20,
    status?: CampaignStatus,
    search?: string,
    sort_by = 'created_at',
    sort_order: 'asc' | 'desc' = 'desc'
  ): Promise<CampaignListResponse> {
    const params: Record<string, unknown> = { page, page_size, sort_by, sort_order };
    if (status) params.status = status;
    if (search) params.search = search;
    const response = await api.get<CampaignListResponse>('/campaigns', { params });
    return response.data;
  },

  // Get single campaign
  async getCampaign(campaignId: string): Promise<CampaignDetail> {
    const response = await api.get<CampaignDetail>(`/campaigns/${campaignId}`);
    return response.data;
  },

  // Create campaign draft
  async createCampaign(data: CampaignCreate): Promise<Campaign> {
    const response = await api.post<Campaign>('/campaigns', data);
    return response.data;
  },

  // Update campaign
  async updateCampaign(campaignId: string, data: CampaignUpdate): Promise<Campaign> {
    const response = await api.patch<Campaign>(`/campaigns/${campaignId}`, data);
    return response.data;
  },

  // Delete campaign (draft only)
  async deleteCampaign(campaignId: string): Promise<void> {
    await api.delete(`/campaigns/${campaignId}`);
  },

  // Schedule campaign
  async scheduleCampaign(campaignId: string, scheduled_at: string): Promise<Campaign> {
    const response = await api.post<Campaign>(`/campaigns/${campaignId}/schedule`, { scheduled_at });
    return response.data;
  },

  // Start campaign immediately
  async startCampaign(campaignId: string): Promise<Campaign> {
    const response = await api.post<Campaign>(`/campaigns/${campaignId}/start`);
    return response.data;
  },

  // Pause campaign
  async pauseCampaign(campaignId: string): Promise<Campaign> {
    const response = await api.post<Campaign>(`/campaigns/${campaignId}/pause`);
    return response.data;
  },

  // Resume campaign
  async resumeCampaign(campaignId: string): Promise<Campaign> {
    const response = await api.post<Campaign>(`/campaigns/${campaignId}/resume`);
    return response.data;
  },

  // Cancel campaign
  async cancelCampaign(campaignId: string): Promise<Campaign> {
    const response = await api.post<Campaign>(`/campaigns/${campaignId}/cancel`);
    return response.data;
  },

  // Get campaign recipients
  async getRecipients(
    campaignId: string,
    page = 1,
    page_size = 50,
    status?: RecipientStatus
  ): Promise<CampaignRecipientsResponse> {
    const params: Record<string, unknown> = { page, page_size };
    if (status) params.status = status;
    const response = await api.get<CampaignRecipientsResponse>(`/campaigns/${campaignId}/recipients`, { params });
    return response.data;
  },

  // Preview recipient filter
  async previewRecipients(campaignId: string, filter: RecipientFilter): Promise<RecipientFilterPreview> {
    const response = await api.post<RecipientFilterPreview>(`/campaigns/${campaignId}/recipients/preview`, filter);
    return response.data;
  },

  // Populate recipients from filter
  async populateRecipients(campaignId: string): Promise<{ count: number }> {
    const response = await api.post<{ count: number }>(`/campaigns/${campaignId}/recipients/populate`);
    return response.data;
  },

  // Get campaign analytics
  async getAnalytics(campaignId: string): Promise<CampaignAnalytics> {
    const response = await api.get<CampaignAnalytics>(`/campaigns/${campaignId}/analytics`);
    return response.data;
  },

  // Send test email
  async sendTest(campaignId: string, emails: string[]): Promise<{ sent: number; errors: string[] }> {
    const response = await api.post<{ sent: number; errors: string[] }>(`/campaigns/${campaignId}/test-send`, { emails });
    return response.data;
  },

  // Get campaign stats summary
  async getStats(): Promise<CampaignStatsResponse> {
    const response = await api.get<CampaignStatsResponse>('/campaigns/stats');
    return response.data;
  },
};

// React Query Hooks

export const useCampaignsQuery = (
  page = 1,
  page_size = 20,
  status?: CampaignStatus,
  search?: string
) => {
  return useQuery({
    queryKey: ['campaigns', page, page_size, status, search],
    queryFn: () => campaignService.listCampaigns(page, page_size, status, search),
  });
};

export const useCampaignQuery = (campaignId: string) => {
  return useQuery({
    queryKey: ['campaigns', campaignId],
    queryFn: () => campaignService.getCampaign(campaignId),
    enabled: !!campaignId,
  });
};

export const useCampaignStatsQuery = () => {
  return useQuery({
    queryKey: ['campaigns', 'stats'],
    queryFn: () => campaignService.getStats(),
  });
};

export const useCampaignRecipientsQuery = (
  campaignId: string,
  page = 1,
  page_size = 50,
  status?: RecipientStatus
) => {
  return useQuery({
    queryKey: ['campaigns', campaignId, 'recipients', page, page_size, status],
    queryFn: () => campaignService.getRecipients(campaignId, page, page_size, status),
    enabled: !!campaignId,
  });
};

export const useCampaignAnalyticsQuery = (campaignId: string) => {
  return useQuery({
    queryKey: ['campaigns', campaignId, 'analytics'],
    queryFn: () => campaignService.getAnalytics(campaignId),
    enabled: !!campaignId,
  });
};

export const useCreateCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CampaignCreate) => campaignService.createCampaign(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
};

export const useUpdateCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ campaignId, data }: { campaignId: string; data: CampaignUpdate }) =>
      campaignService.updateCampaign(campaignId, data),
    onSuccess: (_, { campaignId }) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const useDeleteCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.deleteCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
};

export const useScheduleCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ campaignId, scheduled_at }: { campaignId: string; scheduled_at: string }) =>
      campaignService.scheduleCampaign(campaignId, scheduled_at),
    onSuccess: (_, { campaignId }) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const useStartCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.startCampaign(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const usePauseCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.pauseCampaign(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const useResumeCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.resumeCampaign(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const useCancelCampaignMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.cancelCampaign(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
    },
  });
};

export const usePopulateRecipientsMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => campaignService.populateRecipients(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', campaignId, 'recipients'] });
    },
  });
};

export const useTestSendMutation = () => {
  return useMutation({
    mutationFn: ({ campaignId, emails }: { campaignId: string; emails: string[] }) =>
      campaignService.sendTest(campaignId, emails),
  });
};
