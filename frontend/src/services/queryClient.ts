import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: how long data is considered fresh
      staleTime: 1000 * 60 * 5, // 5 minutes
      // Cache time: how long inactive data stays in cache
      gcTime: 1000 * 60 * 30, // 30 minutes
      // Retry failed requests
      retry: 1,
      // Refetch on window focus for real-time data
      refetchOnWindowFocus: true,
    },
    mutations: {
      // Retry mutations once on failure
      retry: 1,
    },
  },
});

// Query key factory for consistent key management
export const queryKeys = {
  // Messages
  messages: {
    all: ['messages'] as const,
    lists: () => [...queryKeys.messages.all, 'list'] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.messages.lists(), filters] as const,
    details: () => [...queryKeys.messages.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.messages.details(), id] as const,
  },

  // Contacts
  contacts: {
    all: ['contacts'] as const,
    lists: () => [...queryKeys.contacts.all, 'list'] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.contacts.lists(), filters] as const,
    details: () => [...queryKeys.contacts.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.contacts.details(), id] as const,
  },

  // Categories
  categories: {
    all: ['categories'] as const,
    tree: () => [...queryKeys.categories.all, 'tree'] as const,
  },

  // Campaigns
  campaigns: {
    all: ['campaigns'] as const,
    lists: () => [...queryKeys.campaigns.all, 'list'] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.campaigns.lists(), filters] as const,
    details: () => [...queryKeys.campaigns.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.campaigns.details(), id] as const,
  },

  // Workflows
  workflows: {
    all: ['workflows'] as const,
    lists: () => [...queryKeys.workflows.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.workflows.all, 'detail', id] as const,
  },

  // Forms
  forms: {
    all: ['forms'] as const,
    lists: () => [...queryKeys.forms.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.forms.all, 'detail', id] as const,
    submissions: (formId: string) =>
      [...queryKeys.forms.all, formId, 'submissions'] as const,
  },

  // Analytics
  analytics: {
    all: ['analytics'] as const,
    sentiment: (params: Record<string, unknown>) =>
      [...queryKeys.analytics.all, 'sentiment', params] as const,
    volume: (params: Record<string, unknown>) =>
      [...queryKeys.analytics.all, 'volume', params] as const,
    categories: (params: Record<string, unknown>) =>
      [...queryKeys.analytics.all, 'categories', params] as const,
    dashboard: () => [...queryKeys.analytics.all, 'dashboard'] as const,
  },

  // Users
  users: {
    all: ['users'] as const,
    me: () => [...queryKeys.users.all, 'me'] as const,
    list: () => [...queryKeys.users.all, 'list'] as const,
  },

  // Roles
  roles: {
    all: ['roles'] as const,
    list: () => [...queryKeys.roles.all, 'list'] as const,
  },

  // API Keys
  apiKeys: {
    all: ['apiKeys'] as const,
    list: () => [...queryKeys.apiKeys.all, 'list'] as const,
  },
};
