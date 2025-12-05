import { api } from './api';
import { Form, FormField, FormFieldType, FormStatus } from '../types';

// Request types
export interface CreateFormRequest {
  name: string;
  description?: string;
  slug: string;
  status?: FormStatus;
  settings?: Record<string, unknown>;
  styling?: Record<string, unknown>;
}

export interface UpdateFormRequest {
  name?: string;
  description?: string;
  slug?: string;
  status?: FormStatus;
  settings?: Record<string, unknown>;
  styling?: Record<string, unknown>;
}

export interface CreateFieldRequest {
  fieldType: FormFieldType;
  label: string;
  placeholder?: string;
  helpText?: string;
  isRequired?: boolean;
  sortOrder?: number;
  validation?: Record<string, unknown>;
  options?: Array<{ value: string; label: string }>;
  conditionalLogic?: Record<string, unknown>;
  mapsToContactField?: string;
  mapsToCustomFieldId?: string;
  settings?: Record<string, unknown>;
}

export interface UpdateFieldRequest {
  label?: string;
  placeholder?: string;
  helpText?: string;
  isRequired?: boolean;
  sortOrder?: number;
  validation?: Record<string, unknown>;
  options?: Array<{ value: string; label: string }>;
  conditionalLogic?: Record<string, unknown>;
  settings?: Record<string, unknown>;
}

// Response types
export interface FormListResponse {
  items: Form[];
  total: number;
}

export interface FormDetailResponse extends Form {
  fields: FormField[];
}

export interface FormSubmission {
  id: string;
  formId: string;
  contactId?: string;
  messageId?: string;
  submittedAt: string;
  fieldValues: Record<string, unknown>;
  status: 'pending' | 'processed' | 'spam';
}

export interface FormSubmissionListResponse {
  items: FormSubmission[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface FormAnalytics {
  formId: string;
  totalSubmissions: number;
  submissionsToday: number;
  submissionsThisWeek: number;
  completionRate?: number;
  avgCompletionTimeSeconds?: number;
}

// API functions
export const formsService = {
  // Form CRUD
  async listForms(status?: FormStatus): Promise<FormListResponse> {
    const params = status ? { status } : {};
    const response = await api.get<FormListResponse>('/forms', { params });
    return response.data;
  },

  async getForm(formId: string): Promise<FormDetailResponse> {
    const response = await api.get<FormDetailResponse>(`/forms/${formId}`);
    return response.data;
  },

  async createForm(data: CreateFormRequest): Promise<Form> {
    const response = await api.post<Form>('/forms', data);
    return response.data;
  },

  async updateForm(formId: string, data: UpdateFormRequest): Promise<Form> {
    const response = await api.patch<Form>(`/forms/${formId}`, data);
    return response.data;
  },

  async deleteForm(formId: string): Promise<void> {
    await api.delete(`/forms/${formId}`);
  },

  async duplicateForm(formId: string, newName: string, newSlug: string): Promise<Form> {
    const response = await api.post<Form>(
      `/forms/${formId}/duplicate`,
      null,
      { params: { new_name: newName, new_slug: newSlug } }
    );
    return response.data;
  },

  // Field CRUD
  async addField(formId: string, data: CreateFieldRequest): Promise<FormField> {
    // Convert camelCase to snake_case for API
    const payload = {
      field_type: data.fieldType,
      label: data.label,
      placeholder: data.placeholder,
      help_text: data.helpText,
      is_required: data.isRequired,
      sort_order: data.sortOrder,
      validation: data.validation,
      options: data.options,
      conditional_logic: data.conditionalLogic,
      maps_to_contact_field: data.mapsToContactField,
      maps_to_custom_field_id: data.mapsToCustomFieldId,
      settings: data.settings,
    };
    const response = await api.post<FormField>(`/forms/${formId}/fields`, payload);
    return response.data;
  },

  async updateField(formId: string, fieldId: string, data: UpdateFieldRequest): Promise<FormField> {
    // Convert camelCase to snake_case for API
    const payload: Record<string, unknown> = {};
    if (data.label !== undefined) payload.label = data.label;
    if (data.placeholder !== undefined) payload.placeholder = data.placeholder;
    if (data.helpText !== undefined) payload.help_text = data.helpText;
    if (data.isRequired !== undefined) payload.is_required = data.isRequired;
    if (data.sortOrder !== undefined) payload.sort_order = data.sortOrder;
    if (data.validation !== undefined) payload.validation = data.validation;
    if (data.options !== undefined) payload.options = data.options;
    if (data.conditionalLogic !== undefined) payload.conditional_logic = data.conditionalLogic;
    if (data.settings !== undefined) payload.settings = data.settings;

    const response = await api.patch<FormField>(`/forms/${formId}/fields/${fieldId}`, payload);
    return response.data;
  },

  async deleteField(formId: string, fieldId: string): Promise<void> {
    await api.delete(`/forms/${formId}/fields/${fieldId}`);
  },

  async reorderFields(formId: string, fieldOrder: string[]): Promise<FormField[]> {
    const response = await api.post<FormField[]>(
      `/forms/${formId}/fields/reorder`,
      fieldOrder
    );
    return response.data;
  },

  // Submissions
  async listSubmissions(
    formId: string,
    page = 1,
    pageSize = 20,
    status?: string
  ): Promise<FormSubmissionListResponse> {
    const params: Record<string, unknown> = { page, page_size: pageSize };
    if (status) params.status = status;
    const response = await api.get<FormSubmissionListResponse>(
      `/forms/${formId}/submissions`,
      { params }
    );
    return response.data;
  },

  // Analytics
  async getAnalytics(formId: string): Promise<FormAnalytics> {
    const response = await api.get<FormAnalytics>(`/forms/${formId}/analytics`);
    return response.data;
  },

  // Public form (for embedding)
  async getPublicForm(tenantSlug: string, formSlug: string): Promise<FormDetailResponse> {
    const response = await api.get<FormDetailResponse>(
      `/forms/public/${tenantSlug}/${formSlug}`
    );
    return response.data;
  },

  async submitForm(formId: string, fieldValues: Record<string, unknown>): Promise<FormSubmission> {
    const response = await api.post<FormSubmission>(`/forms/${formId}/submit`, {
      field_values: fieldValues,
    });
    return response.data;
  },
};

// React Query hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export const useFormsQuery = (status?: FormStatus) => {
  return useQuery({
    queryKey: ['forms', status],
    queryFn: () => formsService.listForms(status),
  });
};

export const useFormQuery = (formId: string) => {
  return useQuery({
    queryKey: ['forms', formId],
    queryFn: () => formsService.getForm(formId),
    enabled: !!formId,
  });
};

export const useFormSubmissionsQuery = (
  formId: string,
  page = 1,
  pageSize = 20,
  status?: string
) => {
  return useQuery({
    queryKey: ['forms', formId, 'submissions', page, pageSize, status],
    queryFn: () => formsService.listSubmissions(formId, page, pageSize, status),
    enabled: !!formId,
  });
};

export const useFormAnalyticsQuery = (formId: string) => {
  return useQuery({
    queryKey: ['forms', formId, 'analytics'],
    queryFn: () => formsService.getAnalytics(formId),
    enabled: !!formId,
  });
};

export const useCreateFormMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: formsService.createForm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
    },
  });
};

export const useUpdateFormMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, data }: { formId: string; data: UpdateFormRequest }) =>
      formsService.updateForm(formId, data),
    onSuccess: (_, { formId }) => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
      queryClient.invalidateQueries({ queryKey: ['forms', formId] });
    },
  });
};

export const useDeleteFormMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: formsService.deleteForm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
    },
  });
};

export const useDuplicateFormMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, newName, newSlug }: { formId: string; newName: string; newSlug: string }) =>
      formsService.duplicateForm(formId, newName, newSlug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] });
    },
  });
};

export const useAddFieldMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, data }: { formId: string; data: CreateFieldRequest }) =>
      formsService.addField(formId, data),
    onSuccess: (_, { formId }) => {
      queryClient.invalidateQueries({ queryKey: ['forms', formId] });
    },
  });
};

export const useUpdateFieldMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, fieldId, data }: { formId: string; fieldId: string; data: UpdateFieldRequest }) =>
      formsService.updateField(formId, fieldId, data),
    onSuccess: (_, { formId }) => {
      queryClient.invalidateQueries({ queryKey: ['forms', formId] });
    },
  });
};

export const useDeleteFieldMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, fieldId }: { formId: string; fieldId: string }) =>
      formsService.deleteField(formId, fieldId),
    onSuccess: (_, { formId }) => {
      queryClient.invalidateQueries({ queryKey: ['forms', formId] });
    },
  });
};

export const useReorderFieldsMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formId, fieldOrder }: { formId: string; fieldOrder: string[] }) =>
      formsService.reorderFields(formId, fieldOrder),
    onSuccess: (_, { formId }) => {
      queryClient.invalidateQueries({ queryKey: ['forms', formId] });
    },
  });
};
