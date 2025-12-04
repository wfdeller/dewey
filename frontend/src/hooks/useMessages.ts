import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, getErrorMessage } from '../services/api';
import { queryKeys } from '../services/queryClient';
import type { Message, PaginatedResponse, PaginationParams } from '../types';

interface MessageFilters extends PaginationParams {
  source?: string;
  sentiment?: string;
  categoryId?: string;
  search?: string;
  dateFrom?: string;
  dateTo?: string;
  dateRange?: [string, string];
}

// Fetch messages list
export function useMessages(filters: MessageFilters = {}) {
  // Build query params, handling dateRange specially
  const queryParams: Record<string, unknown> = { ...filters };
  if (filters.dateRange) {
    queryParams.dateFrom = filters.dateRange[0];
    queryParams.dateTo = filters.dateRange[1];
    delete queryParams.dateRange;
  }

  return useQuery({
    queryKey: queryKeys.messages.list(queryParams),
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(queryParams).forEach(([key, value]) => {
        if (value !== undefined && value !== '') {
          params.append(key, String(value));
        }
      });
      const { data } = await api.get<PaginatedResponse<Message>>(
        `/messages?${params.toString()}`
      );
      return data;
    },
  });
}

// Fetch single message
export function useMessage(id: string) {
  return useQuery({
    queryKey: queryKeys.messages.detail(id),
    queryFn: async () => {
      const { data } = await api.get<Message>(`/messages/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

// Create message
interface CreateMessageInput {
  senderEmail: string;
  senderName?: string;
  subject: string;
  bodyText: string;
  bodyHtml?: string;
  source?: string;
  metadata?: Record<string, unknown>;
}

export function useCreateMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateMessageInput) => {
      const { data } = await api.post<Message>('/messages', input);
      return data;
    },
    onSuccess: () => {
      // Invalidate messages list to refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.messages.lists() });
    },
    onError: (error) => {
      console.error('Failed to create message:', getErrorMessage(error));
    },
  });
}

// Update message (e.g., assign category)
interface UpdateMessageInput {
  id: string;
  categoryIds?: string[];
  contactId?: string;
}

export function useUpdateMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...input }: UpdateMessageInput) => {
      const { data } = await api.patch<Message>(`/messages/${id}`, input);
      return data;
    },
    onSuccess: (data) => {
      // Update cache
      queryClient.setQueryData(queryKeys.messages.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: queryKeys.messages.lists() });
    },
  });
}

// Bulk actions
export function useBulkAssignCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      messageIds,
      categoryId,
    }: {
      messageIds: string[];
      categoryId: string;
    }) => {
      await api.post('/messages/bulk/assign-category', {
        message_ids: messageIds,
        category_id: categoryId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.messages.all });
    },
  });
}
