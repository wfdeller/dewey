import { api } from './api';

// Email Provider types
export type EmailProvider = 'smtp' | 'ses' | 'graph' | 'sendgrid';

// Email Configuration
export interface EmailConfig {
  id: string;
  tenant_id: string;
  provider: EmailProvider;
  from_email: string;
  from_name?: string;
  reply_to_email?: string;
  is_active: boolean;
  max_sends_per_hour: number;
  last_send_at?: string;
  last_error?: string;
}

export interface EmailConfigCreate {
  provider: EmailProvider;
  from_email: string;
  from_name?: string;
  reply_to_email?: string;
  config: Record<string, unknown>;
  max_sends_per_hour?: number;
  is_active?: boolean;
}

export interface EmailConfigUpdate {
  provider?: EmailProvider;
  from_email?: string;
  from_name?: string;
  reply_to_email?: string;
  config?: Record<string, unknown>;
  max_sends_per_hour?: number;
  is_active?: boolean;
}

// SMTP specific config
export interface SMTPConfig {
  host: string;
  port: number;
  username?: string;
  password?: string;
  use_tls: boolean;
  use_ssl: boolean;
}

// SES specific config
export interface SESConfig {
  region: string;
  access_key_id: string;
  secret_access_key: string;
  configuration_set?: string;
}

// Graph specific config
export interface GraphConfig {
  client_id: string;
  client_secret: string;
  tenant_id: string;
  user_id: string; // mailbox email address
}

// SendGrid specific config
export interface SendGridConfig {
  api_key: string;
}

// Email Template
export interface EmailTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  subject: string;
  body_html: string;
  body_text?: string;
  design_json?: Record<string, unknown>;
  default_form_id?: string;
  form_link_single_use: boolean;
  form_link_expires_days?: number;
  attachments: Array<{ name: string; url: string; content_type: string }>;
  is_active: boolean;
  send_count: number;
  last_sent_at?: string;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateCreate {
  name: string;
  description?: string;
  subject: string;
  body_html: string;
  body_text?: string;
  design_json?: Record<string, unknown>;
  default_form_id?: string;
  form_link_single_use?: boolean;
  form_link_expires_days?: number;
  attachments?: Array<{ name: string; url: string; content_type: string }>;
  is_active?: boolean;
}

export interface EmailTemplateUpdate {
  name?: string;
  description?: string;
  subject?: string;
  body_html?: string;
  body_text?: string;
  design_json?: Record<string, unknown>;
  default_form_id?: string;
  form_link_single_use?: boolean;
  form_link_expires_days?: number;
  attachments?: Array<{ name: string; url: string; content_type: string }>;
  is_active?: boolean;
}

// Sent Email
export interface SentEmail {
  id: string;
  tenant_id: string;
  template_id?: string;
  to_email: string;
  to_name?: string;
  contact_id?: string;
  subject: string;
  triggered_by?: string;
  status: 'pending' | 'sent' | 'delivered' | 'bounced' | 'failed';
  sent_at?: string;
  error_message?: string;
  opened_at?: string;
  clicked_at?: string;
  created_at: string;
}

// Response types
export interface EmailTemplateListResponse {
  items: EmailTemplate[];
  total: number;
}

export interface SentEmailListResponse {
  items: SentEmail[];
  total: number;
  page: number;
  page_size: number;
}

export interface TemplateVariablesResponse {
  variables: Record<string, Record<string, string>>;
}

export interface TemplateValidationResponse {
  is_valid: boolean;
  error?: string;
  variables_used: string[];
}

export interface TemplatePreviewResponse {
  subject: string;
  body_html: string;
  body_text?: string;
}

export interface EmailConfigTestResponse {
  success: boolean;
  message: string;
}

// API functions
export const emailService = {
  // Email Configuration
  async getConfig(): Promise<EmailConfig | null> {
    const response = await api.get<EmailConfig | null>('/email/config');
    return response.data;
  },

  async createOrUpdateConfig(data: EmailConfigCreate): Promise<EmailConfig> {
    const response = await api.post<EmailConfig>('/email/config', {
      ...data,
      max_sends_per_hour: data.max_sends_per_hour ?? 100,
      is_active: data.is_active ?? true,
    });
    return response.data;
  },

  async updateConfig(data: EmailConfigUpdate): Promise<EmailConfig> {
    const response = await api.patch<EmailConfig>('/email/config', data);
    return response.data;
  },

  async testConfig(test_email: string): Promise<EmailConfigTestResponse> {
    const response = await api.post<EmailConfigTestResponse>('/email/config/test', {
      test_email,
    });
    return response.data;
  },

  // Email Templates
  async listTemplates(is_active?: boolean): Promise<EmailTemplateListResponse> {
    const params = is_active !== undefined ? { is_active } : {};
    const response = await api.get<EmailTemplateListResponse>('/email/templates', { params });
    return response.data;
  },

  async getTemplate(templateId: string): Promise<EmailTemplate> {
    const response = await api.get<EmailTemplate>(`/email/templates/${templateId}`);
    return response.data;
  },

  async createTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
    const response = await api.post<EmailTemplate>('/email/templates', {
      ...data,
      form_link_single_use: data.form_link_single_use ?? true,
      form_link_expires_days: data.form_link_expires_days ?? 7,
      is_active: data.is_active ?? true,
    });
    return response.data;
  },

  async updateTemplate(templateId: string, data: EmailTemplateUpdate): Promise<EmailTemplate> {
    const response = await api.patch<EmailTemplate>(`/email/templates/${templateId}`, data);
    return response.data;
  },

  async deleteTemplate(templateId: string): Promise<void> {
    await api.delete(`/email/templates/${templateId}`);
  },

  async duplicateTemplate(templateId: string, new_name: string): Promise<EmailTemplate> {
    const response = await api.post<EmailTemplate>(
      `/email/templates/${templateId}/duplicate`,
      null,
      { params: { new_name } }
    );
    return response.data;
  },

  async validateTemplate(subject: string, body_html: string): Promise<TemplateValidationResponse> {
    const response = await api.post<TemplateValidationResponse>('/email/templates/validate', null, {
      params: { subject, body_html },
    });
    return response.data;
  },

  async previewTemplate(
    subject: string,
    body_html: string,
    body_text?: string,
    sampleData?: {
      contact_name?: string;
      contact_email?: string;
      form_name?: string;
      form_link_url?: string;
    }
  ): Promise<TemplatePreviewResponse> {
    const response = await api.post<TemplatePreviewResponse>('/email/templates/preview', {
      subject,
      body_html,
      body_text,
      contact_name: sampleData?.contact_name,
      contact_email: sampleData?.contact_email,
      form_name: sampleData?.form_name,
      form_link_url: sampleData?.form_link_url,
    });
    return response.data;
  },

  async getTemplateVariables(): Promise<TemplateVariablesResponse> {
    const response = await api.get<TemplateVariablesResponse>('/email/templates/variables');
    return response.data;
  },

  // Sent Emails
  async listSentEmails(
    page = 1,
    page_size = 20,
    status?: string,
    template_id?: string,
    contact_id?: string
  ): Promise<SentEmailListResponse> {
    const params: Record<string, unknown> = { page, page_size };
    if (status) params.status = status;
    if (template_id) params.template_id = template_id;
    if (contact_id) params.contact_id = contact_id;

    const response = await api.get<SentEmailListResponse>('/email/sent', { params });
    return response.data;
  },

  async getSentEmail(emailId: string): Promise<SentEmail> {
    const response = await api.get<SentEmail>(`/email/sent/${emailId}`);
    return response.data;
  },
};

// React Query hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export const useEmailConfigQuery = () => {
  return useQuery({
    queryKey: ['email-config'],
    queryFn: () => emailService.getConfig(),
  });
};

export const useSaveEmailConfigMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EmailConfigCreate) => emailService.createOrUpdateConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-config'] });
    },
  });
};

export const useTestEmailConfigMutation = () => {
  return useMutation({
    mutationFn: (testEmail: string) => emailService.testConfig(testEmail),
  });
};

export const useEmailTemplatesQuery = (is_active?: boolean) => {
  return useQuery({
    queryKey: ['email-templates', is_active],
    queryFn: () => emailService.listTemplates(is_active),
  });
};

export const useEmailTemplateQuery = (templateId: string) => {
  return useQuery({
    queryKey: ['email-templates', templateId],
    queryFn: () => emailService.getTemplate(templateId),
    enabled: !!templateId,
  });
};

export const useCreateEmailTemplateMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EmailTemplateCreate) => emailService.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] });
    },
  });
};

export const useUpdateEmailTemplateMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: EmailTemplateUpdate }) =>
      emailService.updateTemplate(templateId, data),
    onSuccess: (_, { templateId }) => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] });
      queryClient.invalidateQueries({ queryKey: ['email-templates', templateId] });
    },
  });
};

export const useDeleteEmailTemplateMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) => emailService.deleteTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] });
    },
  });
};

export const useSentEmailsQuery = (
  page = 1,
  page_size = 20,
  status?: string,
  template_id?: string,
  contact_id?: string
) => {
  return useQuery({
    queryKey: ['sent-emails', page, page_size, status, template_id, contact_id],
    queryFn: () => emailService.listSentEmails(page, page_size, status, template_id, contact_id),
  });
};

export const useDuplicateEmailTemplateMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, new_name }: { templateId: string; new_name: string }) =>
      emailService.duplicateTemplate(templateId, new_name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] });
    },
  });
};

export const useTemplateVariablesQuery = () => {
  return useQuery({
    queryKey: ['email-template-variables'],
    queryFn: () => emailService.getTemplateVariables(),
  });
};

export const usePreviewTemplateMutation = () => {
  return useMutation({
    mutationFn: (params: {
      subject: string;
      body_html: string;
      body_text?: string;
      sampleData?: {
        contact_name?: string;
        contact_email?: string;
        form_name?: string;
        form_link_url?: string;
      };
    }) => emailService.previewTemplate(params.subject, params.body_html, params.body_text, params.sampleData),
  });
};
