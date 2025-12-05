import { api } from './api';

// Email Provider types
export type EmailProvider = 'smtp' | 'ses' | 'graph' | 'sendgrid';

// Email Configuration
export interface EmailConfig {
  id: string;
  tenantId: string;
  provider: EmailProvider;
  fromEmail: string;
  fromName?: string;
  replyToEmail?: string;
  isActive: boolean;
  maxSendsPerHour: number;
  lastSendAt?: string;
  lastError?: string;
}

export interface EmailConfigCreate {
  provider: EmailProvider;
  fromEmail: string;
  fromName?: string;
  replyToEmail?: string;
  config: Record<string, unknown>;
  maxSendsPerHour?: number;
  isActive?: boolean;
}

export interface EmailConfigUpdate {
  provider?: EmailProvider;
  fromEmail?: string;
  fromName?: string;
  replyToEmail?: string;
  config?: Record<string, unknown>;
  maxSendsPerHour?: number;
  isActive?: boolean;
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
  tenantId: string;
  name: string;
  description?: string;
  subject: string;
  bodyHtml: string;
  bodyText?: string;
  designJson?: Record<string, unknown>;
  defaultFormId?: string;
  formLinkSingleUse: boolean;
  formLinkExpiresDays?: number;
  attachments: Array<{ name: string; url: string; contentType: string }>;
  isActive: boolean;
  sendCount: number;
  lastSentAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface EmailTemplateCreate {
  name: string;
  description?: string;
  subject: string;
  bodyHtml: string;
  bodyText?: string;
  designJson?: Record<string, unknown>;
  defaultFormId?: string;
  formLinkSingleUse?: boolean;
  formLinkExpiresDays?: number;
  attachments?: Array<{ name: string; url: string; contentType: string }>;
  isActive?: boolean;
}

export interface EmailTemplateUpdate {
  name?: string;
  description?: string;
  subject?: string;
  bodyHtml?: string;
  bodyText?: string;
  designJson?: Record<string, unknown>;
  defaultFormId?: string;
  formLinkSingleUse?: boolean;
  formLinkExpiresDays?: number;
  attachments?: Array<{ name: string; url: string; contentType: string }>;
  isActive?: boolean;
}

// Sent Email
export interface SentEmail {
  id: string;
  tenantId: string;
  templateId?: string;
  toEmail: string;
  toName?: string;
  contactId?: string;
  subject: string;
  triggeredBy?: string;
  status: 'pending' | 'sent' | 'delivered' | 'bounced' | 'failed';
  sentAt?: string;
  errorMessage?: string;
  openedAt?: string;
  clickedAt?: string;
  createdAt: string;
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
  pageSize: number;
}

export interface TemplateVariablesResponse {
  variables: Record<string, Record<string, string>>;
}

export interface TemplateValidationResponse {
  isValid: boolean;
  error?: string;
  variablesUsed: string[];
}

export interface TemplatePreviewResponse {
  subject: string;
  bodyHtml: string;
  bodyText?: string;
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
    const payload = {
      provider: data.provider,
      from_email: data.fromEmail,
      from_name: data.fromName,
      reply_to_email: data.replyToEmail,
      config: data.config,
      max_sends_per_hour: data.maxSendsPerHour ?? 100,
      is_active: data.isActive ?? true,
    };
    const response = await api.post<EmailConfig>('/email/config', payload);
    return response.data;
  },

  async updateConfig(data: EmailConfigUpdate): Promise<EmailConfig> {
    const payload: Record<string, unknown> = {};
    if (data.provider !== undefined) payload.provider = data.provider;
    if (data.fromEmail !== undefined) payload.from_email = data.fromEmail;
    if (data.fromName !== undefined) payload.from_name = data.fromName;
    if (data.replyToEmail !== undefined) payload.reply_to_email = data.replyToEmail;
    if (data.config !== undefined) payload.config = data.config;
    if (data.maxSendsPerHour !== undefined) payload.max_sends_per_hour = data.maxSendsPerHour;
    if (data.isActive !== undefined) payload.is_active = data.isActive;

    const response = await api.patch<EmailConfig>('/email/config', payload);
    return response.data;
  },

  async testConfig(testEmail: string): Promise<EmailConfigTestResponse> {
    const response = await api.post<EmailConfigTestResponse>('/email/config/test', {
      test_email: testEmail,
    });
    return response.data;
  },

  // Email Templates
  async listTemplates(isActive?: boolean): Promise<EmailTemplateListResponse> {
    const params = isActive !== undefined ? { is_active: isActive } : {};
    const response = await api.get<EmailTemplateListResponse>('/email/templates', { params });
    return response.data;
  },

  async getTemplate(templateId: string): Promise<EmailTemplate> {
    const response = await api.get<EmailTemplate>(`/email/templates/${templateId}`);
    return response.data;
  },

  async createTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
    const payload = {
      name: data.name,
      description: data.description,
      subject: data.subject,
      body_html: data.bodyHtml,
      body_text: data.bodyText,
      design_json: data.designJson,
      default_form_id: data.defaultFormId,
      form_link_single_use: data.formLinkSingleUse ?? true,
      form_link_expires_days: data.formLinkExpiresDays ?? 7,
      attachments: data.attachments,
      is_active: data.isActive ?? true,
    };
    const response = await api.post<EmailTemplate>('/email/templates', payload);
    return response.data;
  },

  async updateTemplate(templateId: string, data: EmailTemplateUpdate): Promise<EmailTemplate> {
    const payload: Record<string, unknown> = {};
    if (data.name !== undefined) payload.name = data.name;
    if (data.description !== undefined) payload.description = data.description;
    if (data.subject !== undefined) payload.subject = data.subject;
    if (data.bodyHtml !== undefined) payload.body_html = data.bodyHtml;
    if (data.bodyText !== undefined) payload.body_text = data.bodyText;
    if (data.designJson !== undefined) payload.design_json = data.designJson;
    if (data.defaultFormId !== undefined) payload.default_form_id = data.defaultFormId;
    if (data.formLinkSingleUse !== undefined) payload.form_link_single_use = data.formLinkSingleUse;
    if (data.formLinkExpiresDays !== undefined) payload.form_link_expires_days = data.formLinkExpiresDays;
    if (data.attachments !== undefined) payload.attachments = data.attachments;
    if (data.isActive !== undefined) payload.is_active = data.isActive;

    const response = await api.patch<EmailTemplate>(`/email/templates/${templateId}`, payload);
    return response.data;
  },

  async deleteTemplate(templateId: string): Promise<void> {
    await api.delete(`/email/templates/${templateId}`);
  },

  async duplicateTemplate(templateId: string, newName: string): Promise<EmailTemplate> {
    const response = await api.post<EmailTemplate>(
      `/email/templates/${templateId}/duplicate`,
      null,
      { params: { new_name: newName } }
    );
    return response.data;
  },

  async validateTemplate(subject: string, bodyHtml: string): Promise<TemplateValidationResponse> {
    const response = await api.post<TemplateValidationResponse>('/email/templates/validate', null, {
      params: { subject, body_html: bodyHtml },
    });
    return response.data;
  },

  async previewTemplate(
    subject: string,
    bodyHtml: string,
    bodyText?: string,
    sampleData?: {
      contactName?: string;
      contactEmail?: string;
      formName?: string;
      formLinkUrl?: string;
    }
  ): Promise<TemplatePreviewResponse> {
    const response = await api.post<TemplatePreviewResponse>('/email/templates/preview', {
      subject,
      body_html: bodyHtml,
      body_text: bodyText,
      contact_name: sampleData?.contactName,
      contact_email: sampleData?.contactEmail,
      form_name: sampleData?.formName,
      form_link_url: sampleData?.formLinkUrl,
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
    pageSize = 20,
    status?: string,
    templateId?: string,
    contactId?: string
  ): Promise<SentEmailListResponse> {
    const params: Record<string, unknown> = { page, page_size: pageSize };
    if (status) params.status = status;
    if (templateId) params.template_id = templateId;
    if (contactId) params.contact_id = contactId;

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

export const useEmailTemplatesQuery = (isActive?: boolean) => {
  return useQuery({
    queryKey: ['email-templates', isActive],
    queryFn: () => emailService.listTemplates(isActive),
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
  pageSize = 20,
  status?: string,
  templateId?: string,
  contactId?: string
) => {
  return useQuery({
    queryKey: ['sent-emails', page, pageSize, status, templateId, contactId],
    queryFn: () => emailService.listSentEmails(page, pageSize, status, templateId, contactId),
  });
};
