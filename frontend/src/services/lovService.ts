import { api } from './api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';

// Types
export interface LOVItem {
  id: string;
  list_type: string;
  value: string;
  label: string;
  sort_order: number;
  is_active: boolean;
}

export interface LOVTypeMetadata {
  key: string;
  name: string;
  description: string;
}

export interface LOVData {
  prefix: LOVItem[];
  pronoun: LOVItem[];
  language: LOVItem[];
  gender: LOVItem[];
  marital_status: LOVItem[];
  education_level: LOVItem[];
  income_bracket: LOVItem[];
  homeowner_status: LOVItem[];
  voter_status: LOVItem[];
  communication_pref: LOVItem[];
  inactive_reason: LOVItem[];
}

export interface LOVCreateRequest {
  value: string;
  label: string;
  sort_order?: number;
  is_active?: boolean;
}

export interface LOVUpdateRequest {
  value?: string;
  label?: string;
  sort_order?: number;
  is_active?: boolean;
}

// API functions
export const lovService = {
  async getTypes(): Promise<{ types: LOVTypeMetadata[] }> {
    const response = await api.get<{ types: LOVTypeMetadata[] }>('/lov/types');
    return response.data;
  },

  async getAll(): Promise<LOVData> {
    const response = await api.get<LOVData>('/lov');
    return response.data;
  },

  async getActive(): Promise<LOVData> {
    const response = await api.get<LOVData>('/lov/active');
    return response.data;
  },

  async getByType(listType: string, activeOnly = false): Promise<LOVItem[]> {
    const response = await api.get<LOVItem[]>(`/lov/${listType}`, {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  async create(listType: string, data: LOVCreateRequest): Promise<LOVItem> {
    const response = await api.post<LOVItem>(`/lov/${listType}`, data);
    return response.data;
  },

  async update(entryId: string, data: LOVUpdateRequest): Promise<LOVItem> {
    const response = await api.patch<LOVItem>(`/lov/${entryId}`, data);
    return response.data;
  },

  async delete(entryId: string): Promise<void> {
    await api.delete(`/lov/${entryId}`);
  },

  async reorder(listType: string, entryIds: string[]): Promise<LOVItem[]> {
    const response = await api.post<LOVItem[]>(`/lov/${listType}/reorder`, entryIds);
    return response.data;
  },

  async seed(): Promise<{ message: string; seeded_count: number; list_types: string[] }> {
    const response = await api.post<{ message: string; seeded_count: number; list_types: string[] }>('/lov/seed');
    return response.data;
  },
};

// React Query hooks

// Get all LOV data (for admin management)
export const useLOVQuery = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['lov', 'all'],
    queryFn: () => lovService.getAll(),
    enabled: isAuthenticated,
  });
};

// Get only active LOV data (for form dropdowns)
export const useActiveLOVQuery = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ['lov', 'active'],
    queryFn: () => lovService.getActive(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes (LOV changes rarely)
    enabled: isAuthenticated,
  });
};

// Get LOV types metadata
export const useLOVTypesQuery = () => {
  return useQuery({
    queryKey: ['lov', 'types'],
    queryFn: () => lovService.getTypes(),
    staleTime: 30 * 60 * 1000, // Cache for 30 minutes (types are static)
  });
};

// Get LOV by type
export const useLOVByTypeQuery = (listType: string, activeOnly = false) => {
  return useQuery({
    queryKey: ['lov', listType, activeOnly],
    queryFn: () => lovService.getByType(listType, activeOnly),
    enabled: !!listType,
  });
};

// Create LOV entry
export const useCreateLOVMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ listType, data }: { listType: string; data: LOVCreateRequest }) =>
      lovService.create(listType, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lov'] });
    },
  });
};

// Update LOV entry
export const useUpdateLOVMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: LOVUpdateRequest }) =>
      lovService.update(entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lov'] });
    },
  });
};

// Delete LOV entry
export const useDeleteLOVMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => lovService.delete(entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lov'] });
    },
  });
};

// Reorder LOV entries
export const useReorderLOVMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ listType, entryIds }: { listType: string; entryIds: string[] }) =>
      lovService.reorder(listType, entryIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lov'] });
    },
  });
};

// Seed default LOV entries
export const useSeedLOVMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => lovService.seed(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lov'] });
    },
  });
};

// Helper to convert LOV items to Ant Design Select options
export const toSelectOptions = (items: LOVItem[] | undefined) => {
  if (!items) return [];
  return items
    .filter((item) => item.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({
      value: item.value,
      label: item.label,
    }));
};
