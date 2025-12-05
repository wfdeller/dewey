import { api } from './api';
import { Contact, SentimentLabel } from '../types';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Request types
export interface CreateContactRequest {
  email: string;
  name?: string;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
    country?: string;
    district?: string;
  };
  tags?: string[];
  notes?: string;
  custom_fields?: Record<string, unknown>;
}

export interface UpdateContactRequest {
  name?: string;
  email?: string;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
    country?: string;
    district?: string;
  };
  tags?: string[];
  notes?: string;
  custom_fields?: Record<string, unknown>;
}

export interface ContactFilters {
  search?: string;
  tag?: string;
  min_messages?: number;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface BulkTagRequest {
  contact_ids: string[];
  tag: string;
}

// Response types
export interface CustomFieldValue {
  field_key: string;
  field_name: string;
  field_type: string;
  value: string | number | boolean | string[] | null;
}

export interface ContactDetailResponse {
  id: string;
  tenant_id: string;
  email: string;
  name?: string;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
    country?: string;
    district?: string;
  };
  first_contact_at?: string;
  last_contact_at?: string;
  message_count: number;
  avg_sentiment?: number;
  tags: string[];
  notes?: string;
  custom_fields: CustomFieldValue[];
  created_at: string;
}

export interface ContactListResponse {
  items: Contact[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ContactMessageSummary {
  id: string;
  subject: string;
  sender_email: string;
  source: string;
  processing_status: string;
  received_at: string;
  sentiment_label?: SentimentLabel;
}

export interface ContactMessagesResponse {
  items: ContactMessageSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TimelineEntry {
  date: string;
  message_count: number;
  avg_sentiment: number | null;
}

export interface ContactTimelineResponse {
  contact_id: string;
  entries: TimelineEntry[];
}

export interface BulkTagResponse {
  success_count: number;
  failed_count: number;
}

// API functions
export const contactsService = {
  async listContacts(
    page = 1,
    page_size = 20,
    filters?: ContactFilters
  ): Promise<ContactListResponse> {
    const params: Record<string, unknown> = { page, page_size };
    if (filters?.search) params.search = filters.search;
    if (filters?.tag) params.tag = filters.tag;
    if (filters?.min_messages) params.min_messages = filters.min_messages;
    if (filters?.sentiment) params.sentiment = filters.sentiment;
    if (filters?.sort_by) params.sort_by = filters.sort_by;
    if (filters?.sort_order) params.sort_order = filters.sort_order;

    const response = await api.get<ContactListResponse>('/contacts', { params });
    return response.data;
  },

  async getContact(contactId: string): Promise<ContactDetailResponse> {
    const response = await api.get<ContactDetailResponse>(`/contacts/${contactId}`);
    return response.data;
  },

  async createContact(data: CreateContactRequest): Promise<Contact> {
    const response = await api.post<Contact>('/contacts', data);
    return response.data;
  },

  async updateContact(contactId: string, data: UpdateContactRequest): Promise<Contact> {
    const response = await api.patch<Contact>(`/contacts/${contactId}`, data);
    return response.data;
  },

  async deleteContact(contactId: string): Promise<void> {
    await api.delete(`/contacts/${contactId}`);
  },

  async getContactMessages(
    contactId: string,
    page = 1,
    page_size = 20
  ): Promise<ContactMessagesResponse> {
    const response = await api.get<ContactMessagesResponse>(
      `/contacts/${contactId}/messages`,
      { params: { page, page_size } }
    );
    return response.data;
  },

  async getContactTimeline(
    contactId: string,
    days = 30
  ): Promise<ContactTimelineResponse> {
    const response = await api.get<ContactTimelineResponse>(
      `/contacts/${contactId}/timeline`,
      { params: { days } }
    );
    return response.data;
  },

  async addTag(contactId: string, tag: string): Promise<Contact> {
    const response = await api.post<Contact>(
      `/contacts/${contactId}/tags`,
      null,
      { params: { tag } }
    );
    return response.data;
  },

  async removeTag(contactId: string, tag: string): Promise<Contact> {
    const response = await api.delete<Contact>(`/contacts/${contactId}/tags/${tag}`);
    return response.data;
  },

  async bulkAddTag(data: BulkTagRequest): Promise<BulkTagResponse> {
    const response = await api.post<BulkTagResponse>('/contacts/bulk-tag', data);
    return response.data;
  },

  async mergeContacts(
    sourceContactIds: string[],
    targetContactId: string
  ): Promise<Contact> {
    const response = await api.post<Contact>('/contacts/merge', null, {
      params: {
        source_contact_ids: sourceContactIds,
        target_contact_id: targetContactId,
      },
    });
    return response.data;
  },
};

// React Query hooks
export const useContactsQuery = (
  page = 1,
  pageSize = 20,
  filters?: ContactFilters
) => {
  return useQuery({
    queryKey: ['contacts', page, pageSize, filters],
    queryFn: () => contactsService.listContacts(page, pageSize, filters),
  });
};

export const useContactQuery = (contactId: string) => {
  return useQuery({
    queryKey: ['contacts', contactId],
    queryFn: () => contactsService.getContact(contactId),
    enabled: !!contactId,
  });
};

export const useContactMessagesQuery = (
  contactId: string,
  page = 1,
  pageSize = 20
) => {
  return useQuery({
    queryKey: ['contacts', contactId, 'messages', page, pageSize],
    queryFn: () => contactsService.getContactMessages(contactId, page, pageSize),
    enabled: !!contactId,
  });
};

export const useContactTimelineQuery = (contactId: string, days = 30) => {
  return useQuery({
    queryKey: ['contacts', contactId, 'timeline', days],
    queryFn: () => contactsService.getContactTimeline(contactId, days),
    enabled: !!contactId,
  });
};

export const useCreateContactMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contactsService.createContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
};

export const useUpdateContactMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, data }: { contactId: string; data: UpdateContactRequest }) =>
      contactsService.updateContact(contactId, data),
    onSuccess: (_, { contactId }) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['contacts', contactId] });
    },
  });
};

export const useDeleteContactMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contactsService.deleteContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
};

export const useAddTagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, tag }: { contactId: string; tag: string }) =>
      contactsService.addTag(contactId, tag),
    onSuccess: (_, { contactId }) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['contacts', contactId] });
    },
  });
};

export const useRemoveTagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, tag }: { contactId: string; tag: string }) =>
      contactsService.removeTag(contactId, tag),
    onSuccess: (_, { contactId }) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['contacts', contactId] });
    },
  });
};

export const useBulkAddTagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contactsService.bulkAddTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
};

export const useMergeContactsMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceIds, targetId }: { sourceIds: string[]; targetId: string }) =>
      contactsService.mergeContacts(sourceIds, targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
};
