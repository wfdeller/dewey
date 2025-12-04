// Common types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

// Message types
export type MessageSource = 'email' | 'form' | 'api' | 'upload';
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SentimentLabel = 'positive' | 'neutral' | 'negative';

export interface Message {
  id: string;
  tenantId: string;
  contactId?: string;
  campaignId?: string;
  subject: string;
  bodyText: string;
  bodyHtml?: string;
  senderEmail: string;
  senderName?: string;
  source: MessageSource;
  processingStatus: ProcessingStatus;
  isTemplateMatch: boolean;
  templateSimilarityScore?: number;
  receivedAt: string;
  processedAt?: string;
  analysis?: Analysis;
}

export interface Analysis {
  id: string;
  messageId: string;
  sentimentScore: number;
  sentimentLabel: SentimentLabel;
  sentimentConfidence: number;
  summary: string;
  entities: Entity[];
  suggestedCategories: SuggestedCategory[];
  suggestedResponse?: string;
  urgencyScore: number;
  aiProvider: string;
  aiModel: string;
}

export interface Entity {
  type: 'person' | 'org' | 'location' | 'topic';
  value: string;
  confidence: number;
}

export interface SuggestedCategory {
  categoryId: string;
  confidence: number;
}

// Contact types
export interface Contact {
  id: string;
  tenantId: string;
  email: string;
  name?: string;
  phone?: string;
  address?: Address;
  firstContactAt?: string;
  lastContactAt?: string;
  messageCount: number;
  avgSentiment?: number;
  tags: string[];
  customFields?: Record<string, unknown>;
}

export interface Address {
  street?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  district?: string;
}

// Category types
export interface Category {
  id: string;
  tenantId: string;
  parentId?: string;
  name: string;
  description?: string;
  color: string;
  isActive: boolean;
  sortOrder: number;
  keywords: string[];
  children?: Category[];
}

// Campaign types
export type CampaignStatus = 'detected' | 'confirmed' | 'dismissed';
export type DetectionType = 'template' | 'coordinated' | 'manual';

export interface Campaign {
  id: string;
  tenantId: string;
  name: string;
  status: CampaignStatus;
  detectionType: DetectionType;
  templateSubjectPattern?: string;
  firstSeenAt: string;
  lastSeenAt: string;
  messageCount: number;
  uniqueSenders: number;
  sourceOrganization?: string;
}

// Workflow types
export type ExecutionStatus = 'running' | 'completed' | 'failed';

export interface Workflow {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  isActive: boolean;
  priority: number;
  trigger: WorkflowTrigger;
  actions: WorkflowAction[];
}

export interface WorkflowTrigger {
  conditions: TriggerCondition[];
  match: 'all' | 'any';
}

export interface TriggerCondition {
  field: string;
  operator: 'eq' | 'ne' | 'lt' | 'gt' | 'in' | 'contains';
  value: unknown;
}

export interface WorkflowAction {
  type: 'auto_reply' | 'assign' | 'add_category' | 'notify' | 'webhook' | 'update_field';
  [key: string]: unknown;
}

// Form types
export type FormStatus = 'draft' | 'published' | 'archived';
export type FormFieldType =
  | 'text'
  | 'textarea'
  | 'email'
  | 'phone'
  | 'select'
  | 'multi_select'
  | 'radio'
  | 'checkbox'
  | 'date'
  | 'number'
  | 'rating'
  | 'nps'
  | 'file_upload'
  | 'hidden';

export interface Form {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  slug: string;
  status: FormStatus;
  settings: FormSettings;
  styling: FormStyling;
  fields?: FormField[];
}

export interface FormSettings {
  submitButtonText?: string;
  successMessage?: string;
  redirectUrl?: string;
  notificationEmails?: string[];
  autoResponseEnabled?: boolean;
  captchaEnabled?: boolean;
}

export interface FormStyling {
  primaryColor?: string;
  fontFamily?: string;
  customCss?: string;
}

export interface FormField {
  id: string;
  formId: string;
  fieldType: FormFieldType;
  label: string;
  placeholder?: string;
  helpText?: string;
  isRequired: boolean;
  sortOrder: number;
  validation?: Record<string, unknown>;
  options?: FieldOption[];
}

export interface FieldOption {
  value: string;
  label: string;
}

// User types
export interface User {
  id: string;
  tenantId: string;
  email: string;
  name: string;
  isActive: boolean;
  azureAdOid?: string;
  roles?: Role[];
}

export interface Role {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  isSystem: boolean;
  permissions: string[];
  azureAdGroupId?: string;
}

// API Key types
export interface APIKey {
  id: string;
  tenantId: string;
  name: string;
  keyPrefix: string;
  scopes: string[];
  rateLimit: number;
  expiresAt?: string;
  allowedIps?: string[];
  lastUsedAt?: string;
  usageCount: number;
}

// Analytics types
export interface DashboardStats {
  totalMessages: number;
  messagesThisWeek: number;
  avgSentiment: number;
  activeCampaigns: number;
  pendingMessages: number;
}

export interface SentimentTrend {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  avgScore: number;
}

export interface CategoryBreakdown {
  categoryId: string;
  categoryName: string;
  count: number;
  percentage: number;
}

export interface VolumeData {
  date: string;
  count: number;
  source?: MessageSource;
}
