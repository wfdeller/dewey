// Common types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// Message types
export type MessageSource = 'email' | 'form' | 'api' | 'upload';
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SentimentLabel = 'positive' | 'neutral' | 'negative';

export interface Message {
  id: string;
  tenant_id: string;
  contact_id?: string;
  campaign_id?: string;
  subject: string;
  body_text: string;
  body_html?: string;
  sender_email: string;
  sender_name?: string;
  source: MessageSource;
  processing_status: ProcessingStatus;
  is_template_match: boolean;
  template_similarity_score?: number;
  received_at: string;
  processed_at?: string;
  analysis?: Analysis;
}

export interface Analysis {
  id: string;
  message_id: string;
  sentiment_score: number;
  sentiment_label: SentimentLabel;
  sentiment_confidence: number;
  summary: string;
  entities: Entity[];
  suggested_categories: SuggestedCategory[];
  suggested_response?: string;
  urgency_score: number;
  ai_provider: string;
  ai_model: string;
}

export interface Entity {
  type: 'person' | 'org' | 'location' | 'topic';
  value: string;
  confidence: number;
}

export interface SuggestedCategory {
  category_id: string;
  confidence: number;
}

// Contact types
export interface Contact {
  id: string;
  tenant_id: string;
  email: string;
  name?: string;
  phone?: string;
  address?: Address;
  first_contact_at?: string;
  last_contact_at?: string;
  message_count: number;
  avg_sentiment?: number;
  tags: string[];
  custom_fields?: Record<string, unknown>;
  created_at: string;
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
  tenant_id: string;
  parent_id?: string;
  name: string;
  description?: string;
  color: string;
  is_active: boolean;
  sort_order: number;
  keywords: string[];
  children?: Category[];
}

// Campaign types
export type CampaignStatus = 'detected' | 'confirmed' | 'dismissed';
export type DetectionType = 'template' | 'coordinated' | 'manual';

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  status: CampaignStatus;
  detection_type: DetectionType;
  template_subject_pattern?: string;
  first_seen_at: string;
  last_seen_at: string;
  message_count: number;
  unique_senders: number;
  source_organization?: string;
}

// Workflow types
export type ExecutionStatus = 'running' | 'completed' | 'failed';

export interface Workflow {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  is_active: boolean;
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
  tenant_id: string;
  name: string;
  description?: string;
  slug: string;
  status: FormStatus;
  settings: FormSettings;
  styling: FormStyling;
  fields?: FormField[];
}

export interface FormSettings {
  submit_button_text?: string;
  success_message?: string;
  redirect_url?: string;
  notification_emails?: string[];
  auto_response_enabled?: boolean;
  captcha_enabled?: boolean;
}

export interface FormStyling {
  primary_color?: string;
  font_family?: string;
  custom_css?: string;
}

export interface FormField {
  id: string;
  form_id: string;
  field_type: FormFieldType;
  label: string;
  placeholder?: string;
  help_text?: string;
  is_required: boolean;
  sort_order: number;
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
  tenant_id: string;
  email: string;
  name: string;
  is_active: boolean;
  azure_ad_oid?: string;
  roles?: Role[];
}

export interface Role {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  is_system: boolean;
  permissions: string[];
  azure_ad_group_id?: string;
}

// API Key types
export interface APIKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit: number;
  expires_at?: string;
  allowed_ips?: string[];
  last_used_at?: string;
  usage_count: number;
}

// Analytics types
export interface DashboardStats {
  total_messages: number;
  messages_this_week: number;
  avg_sentiment: number;
  active_campaigns: number;
  pending_messages: number;
}

export interface SentimentTrend {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  avg_score: number;
}

export interface CategoryBreakdown {
  category_id: string;
  category_name: string;
  count: number;
  percentage: number;
}

export interface VolumeData {
  date: string;
  count: number;
  source?: MessageSource;
}
