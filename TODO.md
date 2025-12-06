# Dewey Implementation TODO

> Comprehensive implementation checklist organized by phase

## Phase 1: Foundation (MVP)

### 1.1 Project Setup

-   [x] Initialize Python project with `pyproject.toml`
-   [x] Set up FastAPI application structure
-   [x] Configure Docker and docker-compose for local development
-   [x] Set up PostgreSQL container
-   [x] Set up Redis container
-   [x] Configure environment variables (.env.example)
-   [ ] Set up pre-commit hooks (black, ruff, mypy)
-   [x] Initialize React frontend with TypeScript (Vite)
-   [x] Install Ant Design and configure theme
    -   [x] `antd`, `@ant-design/icons`, `@ant-design/charts`
    -   [x] Configure ConfigProvider with custom theme tokens
    -   [x] Set up dark mode support
-   [x] Set up ESLint configuration
-   [x] Configure Zustand for UI state management
-   [x] Configure React Query (TanStack Query) for server state

### 1.2 Database & ORM Setup (SQLModel)

-   [x] Install SQLModel, asyncpg, and Alembic
-   [x] Configure async database session management
-   [x] Set up Alembic for migrations with async support
-   [x] Create base SQLModel classes (timestamps, soft delete)
-   [x] Create Tenant model and migration
-   [x] Create User model with tenant relationship
-   [x] Create Message model with full metadata schema (JSON fields)
-   [x] Create Analysis model for AI results
-   [x] Create Category model (hierarchical with parent_id)
-   [x] Create Contact model with aggregates
-   [x] Create CustomFieldDefinition model
-   [x] Create ContactFieldValue model (polymorphic values)
-   [x] Create Campaign model for template detection
-   [x] Create Workflow model (JSON trigger/action schemas)
-   [x] Create WorkflowExecution model
-   [x] Create Form, FormField, FormSubmission models
-   [x] Create APIKey model for service credentials
-   [x] Create Role model (permissions, azure_ad_group_id)
-   [x] Create UserRole model (many-to-many)
-   [ ] Add database indexes for common queries
-   [ ] Implement row-level security policies (tenant_id)
-   [x] Create database seeding script for development
    -   [x] `scripts/seed_dev_data.py` - creates demo tenant, roles, users
    -   [x] Idempotent (safe to run multiple times)
    -   [x] Test accounts with all role types
-   [ ] Generate initial Alembic migration

### 1.3 Authentication & Authorization

-   [x] Implement JWT token generation and validation
-   [x] Implement password hashing (argon2)
-   [x] Add tenant context to JWT claims
-   [x] Create user registration endpoint
-   [x] Create login endpoint
-   [x] Create token refresh endpoint
-   [x] Create /me endpoint (current user info)
-   [x] Create authentication middleware/dependency
-   [x] Implement Azure AD SSO (OIDC)
    -   [x] MSAL integration for token exchange
    -   [x] Azure AD authorization URL generation
    -   [x] OAuth callback handling (GET and POST variants)
    -   [x] User provisioning from Azure AD claims
    -   [x] Tenant matching (Azure tenant → Dewey tenant)
    -   [x] Account linking (Azure AD to existing password account)

### 1.4 Role-Based Access Control (RBAC)

-   [x] Create Role model (SQLModel)
    -   [x] name, permissions (JSON array), is_system, azure_ad_group_id
-   [x] Create UserRole model (user_id, role_id, assigned_at, assigned_by)
-   [x] Define permission constants
    -   [x] messages:read/write/delete/assign
    -   [x] contacts:read/write/delete
    -   [x] categories:read/write
    -   [x] workflows:read/write/execute
    -   [x] analytics:read/export
    -   [x] forms:read/write
    -   [x] settings:read/write, users:read/write, roles:write
    -   [x] api_keys:manage, integrations:manage, billing:manage
-   [x] Create default system roles (owner, admin, manager, agent, viewer)
-   [x] Implement `user.has_permission()` method
-   [x] Implement permission checking class (`PermissionChecker` dependency)
-   [ ] Row-level filtering (agents see assigned messages only)
-   [x] Role management API endpoints
    -   [x] GET /api/v1/roles (list roles)
    -   [x] GET /api/v1/roles/permissions (list available permissions with metadata)
    -   [x] GET /api/v1/roles/:id (get specific role)
    -   [x] POST /api/v1/roles (create custom role)
    -   [x] PATCH /api/v1/roles/:id (update permissions)
    -   [x] DELETE /api/v1/roles/:id (delete custom role)
    -   [x] POST /api/v1/roles/:id/reset (reset system role to defaults)
-   [x] User management API endpoints
    -   [x] GET /api/v1/users (list users with search/filter)
    -   [x] GET /api/v1/users/:id (get user details with roles)
    -   [x] PATCH /api/v1/users/:id (update user profile)
-   [x] User role assignment endpoints
    -   [x] GET /api/v1/users/:id/roles (get user's roles)
    -   [x] POST /api/v1/users/:id/roles (assign role)
    -   [x] DELETE /api/v1/users/:id/roles/:role_id (remove role)
    -   [x] PUT /api/v1/users/:id/roles (replace all roles)
-   [ ] Azure AD group sync
    -   [ ] Link role to Azure AD group ID
    -   [ ] On SSO login, fetch group memberships (Graph API /me/memberOf)
    -   [ ] Auto-assign/remove roles based on group membership
    -   [ ] Add GroupMember.Read.All permission to Azure AD app
-   [x] User management UI (Ant Design)
    -   [x] `Table` listing users with roles, SSO status, active status
    -   [x] Search and pagination
    -   [x] `Modal` for viewing/editing user details
    -   [x] `Select` for role assignment (multi-select)
    -   [x] `Switch` for active/inactive status with confirmation
-   [x] Role management UI (Ant Design)
    -   [x] `Table` listing roles with permissions preview
    -   [x] `Modal` for creating/editing roles
    -   [x] `Collapse` with `Checkbox.Group` for permission selection by category
    -   [x] `Input` for Azure AD group ID linking
    -   [x] Reset to defaults action for system roles

### 1.5 API Keys & Service Credentials

-   [x] Create APIKey model (SQLModel)
    -   [x] key_hash (SHA-256), key_prefix, scopes, rate_limit
    -   [x] expires_at, allowed_ips, last_used_at
-   [x] Implement secure key generation (prefix + random bytes)
-   [x] Implement key validation methods (is_expired, is_ip_allowed, has_scope)
-   [x] API key authentication middleware
    -   [x] Extract from Authorization header (Bearer dwy_xxx)
    -   [x] Hash and lookup
    -   [x] Verify active, not expired, IP allowed
    -   [x] Attach tenant context (AuthContext)
    -   [x] Scope checking per endpoint (ScopeChecker)
    -   [x] Unified auth supporting both JWT and API key (get_auth_context)
-   [x] Rate limiting per API key (Redis-based)
    -   [x] Sliding window counter implementation
    -   [x] Per-key rate limit configuration
    -   [x] 429 response with Retry-After header
-   [x] API key management endpoints
    -   [x] GET /api/v1/api-keys/scopes (list available scopes)
    -   [x] POST /api/v1/api-keys (create, return plaintext once)
    -   [x] GET /api/v1/api-keys (list with prefix only)
    -   [x] GET /api/v1/api-keys/:id (get specific key)
    -   [x] PATCH /api/v1/api-keys/:id (update scopes, rate_limit)
    -   [x] DELETE /api/v1/api-keys/:id (revoke)
    -   [x] POST /api/v1/api-keys/:id/rotate
-   [x] API key management UI (Ant Design)
    -   [x] `Table` listing keys with prefix, scopes, rate limit, expiration, last_used_at
    -   [x] `Modal` for create/edit with scope `Checkbox.Group` by category
    -   [x] Copy-to-clipboard for new key with secure display modal
    -   [x] Confirm dialog for revoke/rotate actions
    -   [x] Expiration status indicators (expired, expiring soon)
    -   [x] IP allowlist configuration (textarea)
    -   [x] Rate limit configuration

### 1.6 Core API Endpoints

-   [x] **Tenants**: POST, GET, PATCH /api/v1/tenants (scaffolded)
-   [x] **Messages**: POST, GET, GET/:id /api/v1/messages (scaffolded)
-   [x] **Categories**: CRUD /api/v1/categories (scaffolded)
    -   [x] GET /categories (list with filter)
    -   [x] GET /categories/tree (hierarchical view)
    -   [x] GET /categories/:id, POST, PATCH, DELETE
    -   [x] POST /categories/:id/reorder
-   [x] **Contacts**: CRUD /api/v1/contacts (scaffolded)
    -   [x] GET /contacts (list with search, pagination)
    -   [x] GET /contacts/:id (with notes, custom fields)
    -   [x] POST, PATCH, DELETE /contacts/:id
    -   [x] GET /contacts/:id/messages, /contacts/:id/timeline
    -   [x] POST/DELETE /contacts/:id/tags
-   [x] **Custom Fields**: CRUD /api/v1/custom-fields (scaffolded)
    -   [x] GET, POST, PATCH, DELETE custom field definitions
    -   [x] POST /custom-fields/:id/reorder
-   [x] **Campaigns**: CRUD /api/v1/campaigns (scaffolded)
    -   [x] GET /campaigns (list with filters)
    -   [x] GET /campaigns/:id, PATCH, DELETE
    -   [x] GET /campaigns/:id/messages
    -   [x] POST /campaigns/:id/merge
    -   [x] POST /campaigns/:id/bulk-respond
    -   [x] GET /campaigns/stats/summary
-   [x] **Workflows**: CRUD /api/v1/workflows (scaffolded)
    -   [x] GET, POST, PATCH, DELETE workflows
    -   [x] POST /workflows/:id/test
    -   [x] POST /workflows/:id/toggle
    -   [x] GET /workflows/:id/executions
    -   [x] GET /workflows/trigger-fields, /workflows/action-types
-   [x] **Forms**: CRUD /api/v1/forms (scaffolded)
    -   [x] GET, POST, PATCH, DELETE forms
    -   [x] POST /forms/:id/duplicate
    -   [x] Form fields: POST, PATCH, DELETE, reorder
    -   [x] GET /forms/:id/submissions
    -   [x] POST /forms/:id/submit (public)
    -   [x] GET /forms/:id/analytics
    -   [x] GET /forms/public/:tenant_slug/:form_slug
-   [x] **Analytics**: /api/v1/analytics (scaffolded)
    -   [x] GET /analytics/dashboard
    -   [x] GET /analytics/sentiment, /analytics/volume
    -   [x] GET /analytics/categories, /analytics/contacts/top
    -   [x] GET /analytics/campaigns/comparison
    -   [x] GET /analytics/custom-fields/:id
    -   [x] GET /analytics/response-times
    -   [x] POST /analytics/export, GET /analytics/export/:id
    -   [x] GET /analytics/datasets (for Power BI)
-   [x] Add pagination to list endpoints (scaffolded with page/page_size params)
-   [x] Add filtering and sorting (scaffolded with query params)
-   [x] Implement request validation (Pydantic schemas created)
-   [ ] Add OpenAPI documentation customization
-   [x] Implement actual database operations
    -   [x] Categories CRUD (was already implemented)
    -   [x] Messages CRUD with filtering, bulk actions, email webhook
    -   [x] Contacts CRUD with custom fields, timeline, merge, tags
    -   [x] Custom Fields CRUD with cascade delete
    -   [x] Campaigns CRUD with merge, bulk respond, confirm/dismiss
    -   [x] Workflows CRUD with trigger evaluation, test against messages
    -   [x] Forms CRUD with submission validation, auto-contact creation
    -   [x] Analytics queries (dashboard, trends, breakdowns, datasets for BI)

### 1.7 Message Intake

#### Microsoft 365 / Graph API Integration (Primary)

-   [ ] Register Azure AD application
    -   [x] Configure redirect URIs (in azure_redirect_uri setting)
    -   [ ] Set API permissions (Mail.Read, User.Read)
    -   [ ] Generate client secret or certificate
-   [ ] Implement Microsoft Graph client service
    -   [ ] OAuth 2.0 token acquisition (client credentials flow)
    -   [ ] Token caching and refresh
-   [ ] Implement mailbox monitoring
    -   [ ] List messages from shared mailbox
    -   [ ] Fetch message content and attachments
    -   [ ] Track sync state (delta queries)
-   [ ] Implement Graph Change Notifications (webhooks)
    -   [ ] Subscription creation endpoint
    -   [ ] Webhook receiver for new mail notifications
    -   [ ] Subscription renewal (before 3-day expiry)
-   [x] Azure AD SSO integration
    -   [x] OIDC authentication flow (MSAL integration)
    -   [x] User provisioning from Azure AD (auto-create user/tenant)
    -   [x] Tenant mapping (Azure tenant → Dewey tenant)
    -   [x] Account linking (Azure AD to existing password account)
-   [ ] O365 connection setup UI (Ant Design)
    -   [ ] Admin consent flow trigger
    -   [ ] Mailbox selection/configuration
    -   [ ] Connection status and sync health

#### Generic Email (IMAP/SMTP fallback)

-   [ ] IMAP connection and polling
-   [ ] Email parsing (headers, body, attachments)
-   [ ] Metadata extraction (SPF, DKIM, DMARC)

#### Common Intake

-   [x] Create API submission endpoint (scaffolded)
-   [ ] Create message queue integration (Azure Service Bus / Redis)
-   [ ] Implement intake worker to process queue
-   [ ] Add rate limiting per tenant
-   [ ] Implement spam detection basics

### 1.8 AI Analysis Pipeline

-   [ ] Define AIProvider protocol/interface
-   [ ] Implement ClaudeProvider
    -   [ ] API client setup
    -   [ ] Prompt engineering for analysis
    -   [ ] Response parsing to AnalysisResult
-   [ ] Create analysis worker
-   [ ] Implement sentiment scoring (-1 to 1)
-   [ ] Implement entity extraction
-   [ ] Implement category suggestions
-   [ ] Implement urgency scoring
-   [ ] Store analysis results
-   [ ] Update Contact aggregates (avg_sentiment)

### 1.9 Basic Frontend (Ant Design)

-   [x] Set up routing (React Router)
-   [x] Create App layout with Ant Design `Layout`, `Menu`, `Sider`
-   [x] Create authentication pages (login)
    -   [x] Use Ant Design `Form`, `Input`, `Button`
    -   [x] Implement auth store with Zustand
-   [x] Build message list page
    -   [x] Ant Design `Table` with pagination
    -   [x] Column sorting and filtering UI
    -   [x] `Tag` components for sentiment (green/yellow/red)
    -   [x] `DatePicker.RangePicker` for date filtering
    -   [x] Row selection for bulk actions
-   [x] Build message detail page
    -   [x] `Descriptions` for metadata display
    -   [x] `Card` sections for content and analysis
    -   [ ] `TreeSelect` for category assignment (needs categories API)
    -   [ ] `Timeline` for workflow execution history
-   [x] Create basic dashboard with stats
    -   [x] `Statistic` cards for key metrics
    -   [ ] `@ant-design/charts` Line chart for volume trend (placeholder)
    -   [ ] `@ant-design/charts` Pie chart for sentiment distribution (placeholder)
-   [x] Create placeholder pages for all routes
    -   [x] Contacts, Categories, Campaigns, Workflows, Forms, Analytics, Settings

---

## Phase 2: Core Features

### 2.1 Form Builder (Ant Design)

-   [x] Create form management API endpoints
-   [x] Build form builder UI
    -   [x] Drag-and-drop with `dnd-kit` library
    -   [x] `Card` for each field with edit/delete actions
    -   [x] `Drawer` for field property editor
    -   [x] `Tabs` for switching between Edit/Preview modes
    -   [x] Live preview using Ant Design form components
-   [x] Implement all field types (map to Ant Design):
    -   [x] text → `Input`, textarea → `Input.TextArea`
    -   [x] email/phone → `Input` with validation
    -   [x] select → `Select`, multi_select → `Select mode="multiple"`
    -   [x] radio → `Radio.Group`, checkbox → `Checkbox.Group`
    -   [x] date → `DatePicker`, number → `InputNumber`
    -   [x] rating → `Rate`, nps → custom with `Radio.Group`
    -   [x] file_upload → `Upload`
-   [ ] Add conditional logic support
-   [ ] Create form styling options (`ConfigProvider` theme)
-   [ ] Build form templates library
-   [x] Implement form submission endpoint (backend)
-   [ ] Create embeddable widget (standalone React build)
-   [x] Create iframe embed option
-   [x] Build form list page (Forms.tsx)
    -   [x] Stats cards, CRUD modals, duplicate form
    -   [x] Dropdown menu with actions (preview, submissions, embed, etc.)
-   [x] Build form submissions viewer (FormSubmissions.tsx)
    -   [x] Paginated table, status filtering, detail modal
    -   [x] Analytics stats (total, today, this week)
-   [x] Create embed code generator page (FormEmbed.tsx)
    -   [x] Direct link, iFrame, and JavaScript widget options
    -   [x] Configurable iFrame dimensions

### 2.1.1 Pre-Identified Form Links

-   [x] Add `form_link` model and migration
    -   [x] Fields: form_id, contact_id, token, is_single_use, expires_at, used_at, use_count
    -   [x] Unique index on token
-   [x] Create token service (`backend/app/services/form_links.py`)
    -   [x] `generate_token()` - cryptographically random URL-safe token (128-bit)
    -   [x] `validate_token()` - check expiration, single-use status
    -   [x] `mark_token_used()` - update usage tracking
-   [x] Backend API endpoints
    -   [x] `POST /forms/{id}/links` - generate link for contact
    -   [x] `POST /forms/{id}/links/bulk` - bulk generate for campaign
    -   [x] `GET /forms/{id}/links` - list links with usage stats
    -   [x] `DELETE /forms/{id}/links/{token}` - revoke link
-   [x] Modify existing endpoints
    -   [x] `GET /forms/public/{tenant}/{slug}?t={token}` - validate token, return contact_id
    -   [x] `POST /forms/{id}/submit?t={token}` - link submission to token's contact
-   [x] Frontend: Form Links management page
    -   [x] Table with contact, created, expires, uses, status
    -   [x] Generate link modal (select contact, options)
    -   [x] Copy link button, revoke action
-   [x] Frontend: Handle token in public form
    -   [x] Extract `t` param from URL
    -   [x] Pass to submission API
    -   [x] Show "form expired" error for invalid tokens (410 Gone)

### 2.1.2 Email System & Auto-Responses

-   [x] Email template model with Jinja2 variable support
    -   [x] Fields: name, subject, body_html, body_text, design_json
    -   [x] Form link integration (default_form_id, single_use, expires_days)
    -   [x] Attachment support
    -   [x] Send count tracking
-   [x] Tenant email configuration model
    -   [x] Per-tenant provider selection (SMTP, SES, Graph, SendGrid)
    -   [x] Provider-specific config storage (encrypted sensitive fields)
    -   [x] Rate limiting (max_sends_per_hour)
    -   [x] From email/name, reply-to configuration
-   [x] Pluggable email provider interface
    -   [x] SMTP provider implementation
    -   [x] AWS SES provider implementation
    -   [x] Microsoft Graph provider implementation
    -   [x] SendGrid provider implementation
-   [x] Template rendering service
    -   [x] Jinja2 template engine with custom filters
    -   [x] Variable substitution: contact, form, form_link, message, tenant, custom
    -   [x] Form link auto-generation in templates
    -   [x] Template validation and variable extraction
-   [x] Email sending service
    -   [x] Provider abstraction with send/validate
    -   [x] Rate limiting enforcement
    -   [x] Sent email logging with status tracking
    -   [x] Error handling and retry support
-   [x] Backend API endpoints (`/api/v1/email/`)
    -   [x] `GET /templates` - list templates
    -   [x] `POST /templates` - create template
    -   [x] `GET /templates/{id}` - get template
    -   [x] `PATCH /templates/{id}` - update template
    -   [x] `DELETE /templates/{id}` - delete template
    -   [x] `POST /templates/{id}/duplicate` - duplicate template
    -   [x] `POST /templates/validate` - validate syntax
    -   [x] `POST /templates/preview` - preview with sample data
    -   [x] `GET /templates/variables` - list available variables
    -   [x] `GET /config` - get tenant email config
    -   [x] `POST /config` - create/update email config
    -   [x] `POST /config/test` - send test email
    -   [x] `GET /sent` - list sent emails
    -   [x] `GET /sent/{id}` - get sent email details
-   [x] Database migration for email tables
-   [ ] Workflow action executor for auto_reply
    -   [ ] Execute auto_reply action with template
    -   [ ] Generate form links for contacts
    -   [ ] Log sent emails
-   [x] Frontend: Email configuration UI in Settings
    -   [x] Provider selection (SMTP, SES, Graph, SendGrid)
    -   [x] Provider-specific configuration forms
    -   [x] Test email functionality
-   [x] Frontend: Email template management page
    -   [x] Template list with stats (total, active, sends)
    -   [x] Create/duplicate/delete modals
    -   [x] Status filtering
-   [x] Frontend: Visual template editor
    -   [x] Rich text editor (React Quill) with formatting toolbar
    -   [x] Variable insertion panel (click-to-copy)
    -   [x] Live preview with sample data
    -   [x] HTML source editing tab
    -   [x] Plain text fallback tab
    -   [x] Settings drawer (name, description, form link options)

### 2.2 Contact Management (Ant Design)

-   [x] Build contacts list page
    -   [x] `Table` with sortable columns (Name, Messages, Sentiment, Tags, Created)
    -   [x] `Input.Search` for quick search by email/name
    -   [x] `Tag` for contact tags display
    -   [x] `Select` for sentiment filtering (positive/neutral/negative)
    -   [x] `Tag` filter input
    -   [x] Stats cards (Total, With Messages, Positive, Negative)
    -   [x] Create contact modal with `Form`, `Input`, `Select mode="tags"`
    -   [x] Row click navigation to detail page
-   [x] Build contact detail page
    -   [x] `Descriptions` for contact info (email, phone, address, dates)
    -   [x] `Statistic` cards (Messages count, Avg Sentiment)
    -   [x] `Table` for message history with pagination
    -   [x] `@ant-design/charts` Line for sentiment timeline (90 days)
    -   [x] `Tabs` for Messages vs Timeline views
    -   [x] Custom fields display in `Card`
    -   [x] Notes display
    -   [x] Edit contact `Modal` with `Form`
    -   [x] Tag management with `Tag closable` and `Input` for adding
    -   [x] Delete contact with `Popconfirm`
    -   [x] Voting History tab with vote summary and election history table
-   [x] Voter File Import wizard (see 2.7)
-   [x] Contact tagging system (`Select mode="tags"`)

### 2.7 Voter File Import System

-   [x] Backend: Database models
    -   [x] Job model (generic background job tracking)
    -   [x] VoteHistory model (per-contact election participation)
    -   [x] New Contact fields (state_voter_id, precinct, school_district, municipal_district, modeled_party)
    -   [x] LOV types (election_type, voting_method, party_ballot)
    -   [x] Database migration
-   [x] Backend: Core services
    -   [x] `job_status.py` - Redis helpers for real-time progress
    -   [x] `ai/field_mapper.py` - AI-powered field mapping with Claude Haiku
    -   [x] `voter_import.py` - Import processing service
-   [x] Backend: API endpoints (`/api/v1/voter-import/`)
    -   [x] POST `/upload` - Upload CSV, create job
    -   [x] POST `/{job_id}/analyze` - Trigger AI analysis
    -   [x] GET `/{job_id}` - Get job status
    -   [x] GET `/{job_id}/progress` - Real-time progress from Redis
    -   [x] PATCH `/{job_id}/confirm` - Confirm mappings & strategy
    -   [x] POST `/{job_id}/start` - Start background processing (enqueues to ARQ)
    -   [x] DELETE `/{job_id}` - Cancel/delete job
    -   [x] GET `/` - List import jobs
    -   [x] GET `/matching-strategies` - List available strategies
-   [x] Backend: Vote history endpoints (in contacts.py)
    -   [x] GET `/contacts/{id}/vote-history` - Paginated history
    -   [x] GET `/contacts/{id}/vote-history/summary` - Aggregated stats
-   [x] Frontend: Voter Import wizard page
    -   [x] `voterImportService.ts` - API client with React Query hooks
    -   [x] `FileUploadStep.tsx` - Drag-drop CSV upload
    -   [x] `FieldMappingStep.tsx` - AI-suggested mappings with override
    -   [x] `MatchingStrategyStep.tsx` - Strategy selection with recommendations
    -   [x] `ImportProgressStep.tsx` - Real-time progress with stats, "Import Submitted" confirmation
    -   [x] `VoterImport.tsx` - 4-step wizard using Ant Design Steps
    -   [x] Route and navigation menu entry
-   [x] Frontend: Vote history display
    -   [x] `voteHistoryService.ts` - API client with React Query hooks
    -   [x] ContactDetail.tsx Voting History tab with summary card and table

### 2.8 ARQ Task Queue System

-   [x] Backend: ARQ integration
    -   [x] Add `arq` dependency to pyproject.toml
    -   [x] `app/core/queue.py` - ARQ pool helpers
    -   [x] `app/workers/tasks.py` - Task definitions (process_voter_import, etc.)
    -   [x] `app/workers/worker.py` - Worker configuration and entry point
    -   [x] Error handling with `_mark_job_failed()` for failed jobs
-   [x] Backend: Job model updates
    -   [x] Add `arq_job_id`, `queued_at`, `error_message` fields
    -   [x] Add `queued` status to job status flow
    -   [x] Migration for ARQ tracking fields
-   [x] Backend: Contact model updates
    -   [x] Make email nullable for voter imports
    -   [x] Partial unique index on (tenant_id, email) WHERE email IS NOT NULL
    -   [x] Auto-compute name from first/middle/last via `__init__` override
    -   [x] Migration for nullable email
-   [x] Backend: Worker settings endpoints
    -   [x] GET `/tenants/settings/worker` - Get worker settings
    -   [x] PATCH `/tenants/settings/worker` - Update worker settings
-   [x] Frontend: Jobs page
    -   [x] Job list with status filtering
    -   [x] Status badges (queued, processing, completed, failed)
    -   [x] Progress display for active jobs
    -   [x] Delete/cancel actions
-   [x] Frontend: Worker settings tab
    -   [x] `WorkerTab.tsx` - Settings form for job queue configuration
    -   [x] Max concurrent jobs setting
    -   [x] Job timeout setting (15m, 30m, 1h, 2h, 4h)
    -   [x] Max retries setting
-   [x] Docker: Worker service
    -   [x] Update docker-compose.yml worker command to use ARQ

### 2.3 Category Management (Ant Design)

-   [ ] Build category tree UI with `Tree` component
-   [ ] Implement drag-and-drop reordering (`Tree draggable`)
-   [ ] `Modal` for add/edit category
-   [ ] `ColorPicker` for category colors
-   [ ] Keyword configuration with `Select mode="tags"`
-   [ ] Bulk message categorization via `Table` row selection

### 2.4 Outbound Email Campaign System

**Note:** Campaign repurposed from inbound detection to outbound email marketing. Inbound coordinated message detection moved to AI analysis.

-   [x] Backend: Database models
    -   [x] Rewrite Campaign model for outbound marketing (template, recipients, scheduling)
    -   [x] Create CampaignRecipient model (per-contact delivery tracking)
    -   [x] Create EmailSuppression model (unsubscribes, bounces)
    -   [x] Create CampaignRecommendation model (AI-driven suggestions)
    -   [x] Add coordinated detection fields to Message model (is_coordinated, coordinated_group_id)
    -   [x] Database migration with legacy table preservation
-   [x] Backend: Campaign API endpoints
    -   [x] Campaign CRUD (create draft, update, delete)
    -   [x] Campaign lifecycle (schedule, start, pause, resume, cancel)
    -   [x] Recipient management (filter preview, populate, manual add)
    -   [x] Campaign analytics endpoints
    -   [x] Test send functionality
-   [x] Backend: Suppression API endpoints
    -   [x] List suppressions with filtering
    -   [x] Add/remove suppressions
    -   [x] Check suppression status
-   [x] Backend: Recommendation API endpoints
    -   [x] List active recommendations
    -   [x] Dismiss/convert recommendations
-   [x] Backend: Webhook endpoints for engagement tracking
    -   [x] SendGrid webhook handler
    -   [x] AWS SES SNS handler
    -   [x] Open tracking (1x1 pixel)
    -   [x] Click tracking (redirect)
    -   [x] Unsubscribe page
-   [x] Backend: ARQ worker tasks
    -   [x] `send_campaign_emails` - batch sending with rate limiting
    -   [x] `process_engagement_event` - handle opens/clicks/bounces
    -   [x] `generate_campaign_recommendations` - AI trend analysis (cron)
    -   [x] `check_scheduled_campaigns` - start scheduled campaigns (cron)
-   [x] Backend: Campaign sending service
    -   [x] Recipient filtering logic
    -   [x] Suppression checking
    -   [x] Batch processing with progress updates
-   [x] Frontend: Campaign list page
    -   [x] Status tabs (Draft, Scheduled, Active, Completed)
    -   [x] Stats preview (sent, opens, clicks)
    -   [x] Actions (Edit, Start, Pause, Delete)
-   [x] Frontend: Campaign wizard (simplified to create modal)
    -   [x] Name, description, template selection
    -   [x] Campaign type selection (standard/ab_test/automated)
    -   [x] Schedule modal for future sends
-   [x] Frontend: Campaign detail/analytics
    -   [x] Stats cards (Recipients, Sent, Delivered, Opens, Clicks, Bounces)
    -   [x] Progress bar for active campaigns
    -   [x] Recipient table with status
    -   [x] Tabs for Recipients, Details, Analytics
-   [x] Frontend: Recommendations panel
    -   [x] Trending topics display with change percentages
    -   [x] Create campaign action (modal with template selection)
    -   [x] Dismiss action

### 2.5 Workflow Engine

-   [ ] Define workflow trigger schema
-   [ ] Define workflow action schema
-   [ ] Implement trigger evaluation engine
-   [ ] Implement actions:
    -   [ ] Send auto-reply email
    -   [ ] Assign to user/team
    -   [ ] Add category
    -   [ ] Send notification
    -   [ ] Webhook call
    -   [ ] Update custom field
-   [ ] Build workflow builder UI
-   [ ] Workflow testing interface
-   [ ] Execution logging

### 2.6 Analytics Dashboard (Ant Design Charts)

-   [ ] `@ant-design/charts` Line for sentiment over time
-   [ ] `@ant-design/charts` Area for message volume
-   [ ] `@ant-design/charts` Pie for category distribution
-   [ ] `Table` for top contacts leaderboard
-   [ ] `@ant-design/charts` Column for custom field breakdown
-   [ ] Campaign vs organic comparison (grouped bar chart)
-   [ ] `DatePicker.RangePicker` for date range selector
-   [ ] `Select` / `TreeSelect` for category/custom field filters
-   [ ] Export reports (`Button` triggering CSV/PDF download)

---

## Phase 3: Marketplace & Scale

### 3.1 Azure Marketplace Integration (Primary)

-   [ ] Create Azure AD multi-tenant application
-   [ ] Register in Microsoft Partner Center
-   [ ] Create Azure Marketplace SaaS offer
    -   [ ] Offer listing (description, screenshots, pricing)
    -   [ ] Technical configuration
    -   [ ] Plan setup (tiers: Free, Pro, Enterprise)
-   [ ] Implement SaaS Fulfillment API v2
    -   [ ] Landing page for marketplace purchases
    -   [ ] Resolve subscription token
    -   [ ] Activate subscription
    -   [ ] Update subscription (plan changes)
    -   [ ] Webhook for subscription lifecycle events
-   [ ] Implement Metered Billing API
    -   [ ] Usage event submission
    -   [ ] Billing dimensions: messages, AI tokens, storage
-   [ ] Azure AD SSO for marketplace customers
-   [ ] Test in Azure Marketplace sandbox
-   [ ] Submit for certification

### 3.2 AWS Marketplace Integration (Secondary)

-   [ ] Create AWS Marketplace listing
-   [ ] Implement SaaS contract API integration
-   [ ] Set up SNS subscription notifications
-   [ ] Create landing page for AWS customers
-   [ ] Implement entitlement service integration
-   [ ] Set up metered billing dimensions
-   [ ] Test subscription lifecycle (subscribe, unsubscribe)

### 3.3 SSO Integration

-   [x] Azure AD SSO (primary, via OIDC)
    -   [x] GET /azure/login - authorization URL generation
    -   [x] GET /azure/callback - OAuth redirect handler
    -   [x] POST /azure/callback - SPA token exchange
    -   [x] POST /azure/link - link Azure to existing account
-   [ ] Implement SAML authentication (for non-Azure customers)
-   [ ] Support Okta
-   [ ] Support Google Workspace
-   [ ] Per-tenant SSO configuration UI

### 3.4 Additional AI Providers

-   [ ] Implement OpenAIProvider
-   [ ] Implement AzureOpenAIProvider
-   [ ] Implement OllamaProvider (self-hosted)
-   [ ] Per-tenant provider selection UI
-   [ ] API key management per tenant
-   [ ] Provider fallback configuration

### 3.5 Advanced Workflows

-   [ ] AI-generated response suggestions
-   [ ] Response approval chains
-   [ ] Scheduled actions
-   [ ] Conditional branching
-   [ ] Workflow templates

### 3.6 Performance & Scaling

-   [ ] Implement database read replicas
-   [ ] Add Redis caching layer
-   [ ] Optimize database queries
-   [ ] Implement connection pooling
-   [ ] Set up auto-scaling policies
-   [ ] Add APM monitoring (DataDog/New Relic)
-   [ ] Performance benchmarking

---

## Phase 4: Enterprise

### 4.1 Multi-Region Deployment

-   [ ] Set up secondary AWS region
-   [ ] Configure database replication
-   [ ] Implement region routing
-   [ ] Active-active deployment
-   [ ] Failover testing

### 4.2 FedRAMP Compliance

-   [ ] Deploy to AWS GovCloud
-   [ ] Implement FIPS 140-2 encryption
-   [ ] Enhanced audit logging (1+ year retention)
-   [ ] Vulnerability scanning setup
-   [ ] Penetration testing
-   [ ] POA&M documentation
-   [ ] 3PAO assessment preparation

### 4.3 Power BI & Analytics Data Layer

-   [ ] Create PostgreSQL views for curated datasets
    -   [ ] `analytics.messages_summary` (core message data with sentiment)
    -   [ ] `analytics.sentiment_trends` (daily/weekly aggregates)
    -   [ ] `analytics.category_breakdown` (messages by category)
    -   [ ] `analytics.contact_analytics` (contact engagement metrics)
    -   [ ] `analytics.campaign_summary` (coordinated campaign stats)
    -   [ ] `analytics.form_analytics` (form submission metrics)
    -   [ ] `analytics.workflow_analytics` (execution success rates)
-   [ ] Implement OData endpoints for Power BI
    -   [ ] Install odata-query or pydantic-odata library
    -   [ ] GET /api/v1/odata/MessagesSummary
    -   [ ] GET /api/v1/odata/SentimentTrends
    -   [ ] GET /api/v1/odata/CategoryBreakdown
    -   [ ] GET /api/v1/odata/ContactAnalytics
    -   [ ] GET /api/v1/odata/CampaignSummary
    -   [ ] GET /api/v1/odata/FormAnalytics
    -   [ ] GET /api/v1/odata/WorkflowAnalytics
    -   [ ] OData $filter, $select, $orderby, $top, $skip support
    -   [ ] Tenant isolation in all OData queries
-   [ ] Add analytics-specific API key scopes
    -   [ ] `analytics:read` - OData and analytics endpoints
    -   [ ] `analytics:export` - bulk export permissions
-   [ ] Create analytics REST endpoints (non-OData alternative)
    -   [ ] GET /api/v1/analytics/datasets - list available datasets
    -   [ ] GET /api/v1/analytics/datasets/{name} - query with filters
    -   [ ] POST /api/v1/analytics/export - bulk export to CSV/JSON
-   [ ] Create Power BI template file (.pbit)
    -   [ ] Pre-configured connection to OData endpoints
    -   [ ] Starter dashboards (sentiment, volume, campaigns)
    -   [ ] Documentation for Power BI setup
-   [ ] Rate limiting for analytics endpoints (per API key)
-   [ ] Query result caching (Redis, configurable TTL)

### 4.4 Advanced Analytics

-   [ ] Data warehouse integration (Redshift/BigQuery)
-   [ ] Custom report builder
-   [ ] Scheduled report delivery
-   [ ] Advanced visualizations
-   [ ] Geographic heat maps
-   [ ] Predictive analytics

### 4.5 White-Label Options

-   [ ] Custom domain support
-   [ ] Branding customization
-   [ ] White-label email sending
-   [ ] Custom CSS/themes

---

## Infrastructure & DevOps

### CI/CD Pipeline

-   [ ] GitHub Actions workflow for backend
-   [ ] GitHub Actions workflow for frontend
-   [ ] Automated testing on PR
-   [ ] Docker image building
-   [ ] Push to ECR
-   [ ] Blue/green deployment to ECS
-   [ ] Database migration automation

### Terraform Infrastructure

-   [ ] VPC configuration
-   [ ] RDS PostgreSQL
-   [ ] ElastiCache Redis
-   [ ] SQS queues
-   [ ] ECS cluster and services
-   [ ] Application Load Balancer
-   [ ] CloudFront distribution
-   [ ] Route 53 DNS
-   [ ] ACM certificates
-   [ ] KMS keys
-   [ ] IAM roles and policies
-   [ ] CloudWatch alarms

### Monitoring & Observability

-   [x] Structured logging (JSON) - configured with structlog
-   [ ] Log aggregation (CloudWatch Logs)
-   [ ] Application metrics
-   [ ] Custom dashboards
-   [ ] Alerting rules
-   [ ] Error tracking (Sentry)
-   [ ] Uptime monitoring

---

## Testing

### Test Infrastructure Setup

-   [ ] Configure pytest with async support (pytest-asyncio)
-   [ ] Set up pytest-cov for coverage reporting
-   [ ] Configure testcontainers for PostgreSQL
-   [ ] Set up test fixtures (db session, auth headers, tenant)
-   [ ] Create factory classes for test data (factory_boy)
-   [ ] Configure Vitest for frontend unit tests
-   [ ] Set up Testing Library for React components
-   [ ] Install and configure Playwright
-   [ ] Set up Locust for load testing
-   [ ] Configure CI test pipeline (GitHub Actions)

### Backend Unit Tests (pytest)

-   [ ] **Models**: Validation, computed properties, relationships
    -   [ ] `test_message_processing_status_transitions`
    -   [ ] `test_contact_avg_sentiment_calculation`
    -   [ ] `test_category_hierarchy_depth`
-   [ ] **Services**: Business logic in isolation
    -   [ ] `test_campaign_detection_similarity_scoring`
    -   [ ] `test_campaign_detection_spike_detection`
    -   [ ] `test_workflow_trigger_evaluation`
    -   [ ] `test_workflow_action_execution`
    -   [ ] `test_metadata_extraction_email_headers`
    -   [ ] `test_metadata_extraction_form_data`
-   [ ] **AI Providers**: Response parsing, error handling
    -   [ ] `test_claude_provider_parse_response`
    -   [ ] `test_claude_provider_handle_rate_limit`
    -   [ ] `test_openai_provider_parse_response`
    -   [ ] `test_ai_provider_fallback`
-   [ ] **Utilities**: Helper functions
    -   [ ] `test_normalize_email`
    -   [ ] `test_hash_content_simhash`
    -   [ ] `test_sanitize_html`

### Backend Integration Tests (pytest + httpx)

-   [ ] **Authentication Flow**
    -   [ ] `test_register_login_access_protected_endpoint`
    -   [ ] `test_api_key_authentication`
    -   [ ] `test_jwt_token_refresh`
    -   [ ] `test_invalid_credentials_rejected`
-   [ ] **Message Pipeline**
    -   [ ] `test_submit_message_queued_for_processing`
    -   [ ] `test_message_analysis_stored_correctly`
    -   [ ] `test_contact_created_from_message`
    -   [ ] `test_campaign_detected_for_similar_messages`
-   [ ] **Multi-tenancy**
    -   [ ] `test_tenant_data_isolation`
    -   [ ] `test_cross_tenant_access_denied`
    -   [ ] `test_tenant_specific_categories`
-   [ ] **CRUD Operations**
    -   [ ] `test_messages_crud_with_filters`
    -   [ ] `test_contacts_crud_with_custom_fields`
    -   [ ] `test_categories_crud_hierarchy`
    -   [ ] `test_workflows_crud_with_triggers`
    -   [ ] `test_forms_crud_with_fields`
-   [ ] **Database**
    -   [ ] `test_migrations_up_down`
    -   [ ] `test_complex_analytics_queries`
    -   [ ] `test_row_level_security_enforcement`

### Frontend Unit Tests (Vitest + Testing Library)

-   [ ] **Hooks**
    -   [ ] `test_useMessages_fetch_and_pagination`
    -   [ ] `test_useAuth_login_logout_state`
    -   [ ] `test_useAnalytics_date_range_filter`
-   [ ] **Components**
    -   [ ] `test_SentimentBadge_renders_correctly`
    -   [ ] `test_MessageList_displays_messages`
    -   [ ] `test_CategoryTree_drag_and_drop`
    -   [ ] `test_FormBuilder_add_remove_fields`
    -   [ ] `test_WorkflowBuilder_trigger_config`
-   [ ] **Utilities**
    -   [ ] `test_formatSentiment`
    -   [ ] `test_buildQueryString`
    -   [ ] `test_validateFormField`

### End-to-End Tests (Playwright)

-   [ ] **Critical User Flows**
    -   [ ] `test_onboarding_register_to_first_message`
    -   [ ] `test_form_submit_view_analysis`
    -   [ ] `test_create_workflow_verify_execution`
    -   [ ] `test_campaign_detection_bulk_respond`
    -   [ ] `test_analytics_filter_export`
-   [ ] **Form Builder Flow**
    -   [ ] `test_create_form_add_fields_publish`
    -   [ ] `test_form_embed_submit_view_response`
    -   [ ] `test_form_conditional_logic`
-   [ ] **Contact Management Flow**
    -   [ ] `test_view_contact_message_history`
    -   [ ] `test_edit_contact_custom_fields`
    -   [ ] `test_bulk_import_contacts`
-   [ ] **Authentication Flows**
    -   [ ] `test_login_logout`
    -   [ ] `test_password_reset`
    -   [ ] `test_sso_login` (when SSO implemented)

### Contract Tests (pact-python)

-   [ ] AI provider request/response contracts
    -   [ ] `test_claude_api_contract`
    -   [ ] `test_openai_api_contract`
-   [ ] Frontend/backend API contracts

### Performance Tests (Locust)

-   [ ] **Load Test Scenarios**
    -   [ ] `test_message_intake_throughput` (target: 100 msg/sec)
    -   [ ] `test_concurrent_api_requests` (target: 500 concurrent)
    -   [ ] `test_analytics_query_under_load`
    -   [ ] `test_form_submission_burst`
-   [ ] **Stress Tests**
    -   [ ] `test_system_recovery_after_overload`
    -   [ ] `test_queue_backpressure_handling`
-   [ ] **Benchmarks**
    -   [ ] `benchmark_ai_analysis_latency`
    -   [ ] `benchmark_campaign_detection_speed`
    -   [ ] `benchmark_database_query_performance`

### Security Tests

-   [ ] `test_sql_injection_prevention`
-   [ ] `test_xss_prevention_in_forms`
-   [ ] `test_authentication_bypass_attempts`
-   [ ] `test_tenant_isolation_enforcement`
-   [ ] `test_api_rate_limiting`
-   [ ] `test_file_upload_validation`

### Test Coverage Targets

| Area                | Target |
| ------------------- | ------ |
| Backend Unit        | 80%    |
| Backend Integration | 70%    |
| Frontend Unit       | 75%    |
| E2E Critical Paths  | 100%   |

---

## Documentation

-   [x] ARCHITECTURE.md - System overview
-   [x] TODO.md - Implementation checklist
-   [x] README.md - Installation guide
-   [ ] API documentation (auto-generated from OpenAPI)
-   [ ] User guide for dashboard
-   [ ] Admin guide for tenant setup
-   [ ] Integration guide for API consumers
-   [ ] Form builder documentation

---

## Progress Tracking

Use this section to track overall progress:

| Phase                  | Status      | Progress |
| ---------------------- | ----------- | -------- |
| Phase 1: Foundation    | In Progress | ~90%     |
| Phase 2: Core Features | In Progress | ~75%     |
| Phase 3: Marketplace   | Not Started | 0%       |
| Phase 4: Enterprise    | Not Started | 0%       |

### Phase 1 Breakdown

| Section                | Status                                               |
| ---------------------- | ---------------------------------------------------- |
| 1.1 Project Setup      | Complete                                             |
| 1.2 Database & ORM     | Models Complete, migrations pending                  |
| 1.3 Authentication     | Complete (JWT, password auth, Azure AD SSO)          |
| 1.4 RBAC               | Complete (APIs, UI for users/roles management)       |
| 1.5 API Keys           | Complete (middleware, rate limiting, endpoints, UI)  |
| 1.6 Core API Endpoints | Complete (all endpoints with full DB operations)     |
| 1.7 Message Intake     | Partial (Azure AD SSO done, Graph API pending)       |
| 1.8 AI Pipeline        | Not Started                                          |
| 1.9 Basic Frontend     | Complete (auth, messages, contacts, forms, settings) |

### Phase 2 Breakdown

| Section                             | Status                                                   |
| ----------------------------------- | -------------------------------------------------------- |
| 2.1 Form Builder                    | Complete (CRUD, drag-drop, preview, embed)               |
| 2.1.1 Pre-Identified Form Links     | Complete                                                 |
| 2.1.2 Email System & Auto-Responses | Complete (backend + frontend UI)                         |
| 2.2 Contact Management              | Complete (list + detail with timeline/messages/voting)   |
| 2.3 Category Management             | Not Started                                              |
| 2.4 Outbound Campaign System        | Complete (backend + frontend)                            |
| 2.5 Workflow Engine                 | Not Started                                              |
| 2.6 Analytics Dashboard             | Not Started                                              |
| 2.7 Voter File Import               | Complete (wizard, AI mapping, ARQ background processing) |
| 2.8 ARQ Task Queue                  | Complete (ARQ integration, worker settings, jobs page)   |

### API Endpoints Summary

| Router                    | Endpoints | Status                                                             |
| ------------------------- | --------- | ------------------------------------------------------------------ |
| /health                   | 1         | Working                                                            |
| /auth                     | 6         | Working                                                            |
| /tenants                  | 5         | Working (includes worker settings)                                 |
| /messages                 | 4         | Working (full CRUD with filtering)                                 |
| /categories               | 7         | Working (full CRUD with hierarchy)                                 |
| /contacts                 | 11        | Working (full CRUD + vote history)                                 |
| /custom-fields            | 5         | Working (full CRUD)                                                |
| /campaigns                | 14        | Working (outbound marketing with lifecycle, recipients, analytics) |
| /suppressions             | 7         | Working (list, add, remove, check, bulk, stats)                    |
| /campaign-recommendations | 5         | Working (list, get, dismiss, convert, stats)                       |
| /webhooks                 | 4         | Working (SendGrid, SES, open tracking, click tracking)             |
| /workflows                | 9         | Working (full CRUD with trigger eval)                              |
| /forms                    | 16        | Working (full CRUD with submissions + form links)                  |
| /analytics                | 12        | Working (dashboard, trends, datasets)                              |
| /roles                    | 6         | Working                                                            |
| /users                    | 7         | Working                                                            |
| /api-keys                 | 7         | Working                                                            |
| /email                    | 15        | Working (templates, config, sent log)                              |
| /voter-import             | 9         | Working (upload, analyze, ARQ import, progress)                    |
| /jobs                     | 4         | Working (list, get, delete, cancel)                                |

---

_Last updated: December 5, 2024_
