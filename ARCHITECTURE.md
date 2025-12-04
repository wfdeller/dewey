# Dewey Architecture

> AI-Powered Communication Processing Platform

## Overview

Dewey is a multi-tenant SaaS platform that processes incoming communications (emails, forms, documents) using AI to analyze sentiment, classify issues, and automate workflows. The platform targets:

-   **Companies** - Customer feedback processing
-   **Elected Officials** - Constituent correspondence management
-   **Government Agencies** - Public inquiry handling

**Deployment Model**: Azure Marketplace (primary), AWS Marketplace (secondary)

**Why Azure First**: Most target customers use Microsoft 365 for email. Azure-first enables:

-   Native O365/Exchange integration via Microsoft Graph API
-   Azure AD SSO for enterprise customers
-   Azure Government for FedRAMP compliance
-   Familiar ecosystem for government/enterprise IT teams

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         INTAKE LAYER                               │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│ Email       │ Web Forms   │ API         │ Webhooks    │ File       │
│ (Graph API) │ (Embedded)  │ (REST)      │ (Zapier)    │ Upload     │
│ (IMAP/SMTP) │             │             │             │            │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────┬──────┘
       │             │             │             │            │
       └─────────────┴─────────────┼─────────────┴────────────┘
                                   ▼
                    ┌──────────────────────────┐
                    │     MESSAGE QUEUE        │
                    │   (SQS / Redis Streams)  │
                    └────────────┬─────────────┘
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                      PROCESSING PIPELINE                           │
├─────────────────┬─────────────────┬─────────────────┬──────────────┤
│ Content         │ AI Analysis     │ Classification  │ Workflow     │
│ Extraction      │ (Sentiment,     │ & Routing       │ Engine       │
│ (text, OCR)     │  Entities)      │                 │              │
└─────────────────┴─────────────────┴─────────────────┴──────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                   │
├────────────────────────┬────────────────────────────────────────────┤
│ PostgreSQL             │ Redis                                      │
│ - Tenants/Orgs         │ - Session cache                            │
│ - Messages             │ - Real-time updates                        │
│ - Classifications      │ - Rate limiting                            │
│ - Workflows            │ - Queue overflow                           │
│ - Audit logs           │                                            │
└────────────────────────┴────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────┤
│ Dashboard       │ Reports &       │ Workflow        │ Admin         │
│ (Real-time)     │ Analytics       │ Builder         │ Console       │
└─────────────────┴─────────────────┴─────────────────┴───────────────┘
```

## Technology Stack

| Component      | Technology                         | Rationale                                                    |
| -------------- | ---------------------------------- | ------------------------------------------------------------ |
| **Backend**    | Python + FastAPI                   | Superior AI/ML ecosystem, async performance                  |
| **ORM**        | SQLModel + Alembic                 | Pydantic integration, less boilerplate, FastAPI-native       |
| **Frontend**   | TypeScript + React                 | Industry standard, rich component ecosystem                  |
| **UI Library** | Ant Design                         | Dashboard-focused, excellent tables/forms/trees, MIT license |
| **Database**   | PostgreSQL                         | Robust, JSON support, row-level security                     |
| **Cache**      | Redis                              | Session storage, real-time pub/sub                           |
| **Queue**      | AWS SQS                            | Managed, auto-scaling, dead letter queues                    |
| **AI**         | Pluggable (Claude, OpenAI, Ollama) | Customer choice, vendor flexibility                          |
| **Deployment** | ECS Fargate                        | Serverless containers, simpler operations                    |
| **Testing**    | pytest, Playwright, Locust         | Comprehensive coverage across all layers                     |

### ORM: SQLModel

SQLModel is chosen over raw SQLAlchemy for its seamless FastAPI integration:

```python
# One class serves as both database model AND API schema
class MessageBase(SQLModel):
    subject: str
    body_text: str
    sender_email: str

class Message(MessageBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id")
    contact_id: UUID | None = Field(foreign_key="contact.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageCreate(MessageBase):
    pass  # Inherits fields for API input

class MessageResponse(MessageBase):
    id: UUID
    created_at: datetime
```

**Benefits:**

-   Created by FastAPI's author - designed for seamless integration
-   Pydantic validation built-in
-   SQLAlchemy power available when needed
-   Alembic migrations work unchanged
-   Async support via `asyncpg`

### UI Library: Ant Design

Ant Design provides dashboard-optimized components that map directly to Dewey's features:

| Dewey Feature       | Ant Design Component                                       |
| ------------------- | ---------------------------------------------------------- |
| Message list        | `Table` with sorting, filtering, pagination, row selection |
| Category hierarchy  | `Tree`, `TreeSelect`                                       |
| Form builder        | `Form`, `Form.List` for dynamic fields                     |
| Analytics dashboard | `@ant-design/charts` (Line, Pie, Bar)                      |
| Workflow builder    | `Card`, `Steps`, combined with drag-drop                   |
| Sentiment display   | `Tag`, `Badge`, `Progress`                                 |
| Contact management  | `Table`, `Descriptions`, `Timeline`                        |
| Settings/Admin      | `Tabs`, `Menu`, `Layout`                                   |

**Key packages:**

```json
{
    "antd": "^5.x",
    "@ant-design/icons": "^5.x",
    "@ant-design/charts": "^2.x"
}
```

## Core Components

### 1. Intake Layer

Handles multiple input channels:

-   **Email (Microsoft 365)**: Primary - Microsoft Graph API integration
-   **Email (Generic)**: IMAP polling + SMTP webhooks for non-O365 customers
-   **Forms**: Built-in form builder with embeddable widgets
-   **API**: REST endpoints for programmatic submission
-   **Webhooks**: Integration with Zapier, Power Automate, custom systems

### Microsoft 365 / Graph API Integration

Primary email integration for enterprise customers using O365/Exchange Online:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Microsoft 365 Tenant                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Exchange    │  │ Azure AD    │  │ Admin Consent           │  │
│  │ Online      │  │ (Users/SSO) │  │ (App Permissions)       │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Microsoft Graph API                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ /me/messages│  │ /users      │  │ Change Notifications    │  │
│  │ Mail.Read   │  │ User.Read   │  │ (Webhooks)              │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Dewey                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Email Sync  │  │ Azure AD    │  │ Real-time Webhook       │  │
│  │ Service     │  │ SSO         │  │ Receiver                │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Graph API Permissions Required:**
| Permission | Type | Purpose |
|------------|------|---------|
| `Mail.Read` | Delegated or Application | Read emails from monitored mailboxes |
| `Mail.ReadBasic` | Application | Read email metadata (lighter permission) |
| `User.Read` | Delegated | Get user profile for SSO |
| `User.Read.All` | Application | List organization users (optional) |

**Integration Options:**

1. **Shared Mailbox Monitoring** (Recommended)

    - Customer creates shared mailbox (e.g., `feedback@contoso.com`)
    - Grants Dewey app access via admin consent
    - Dewey polls or receives webhooks for new messages

2. **Delegated Access**

    - Individual users authorize Dewey to read their mail
    - Per-user OAuth consent flow
    - Good for smaller deployments

3. **Change Notifications (Webhooks)**
    - Real-time notifications when new mail arrives
    - Requires HTTPS endpoint for Microsoft to call
    - Lower latency than polling

**Azure AD App Registration:**

```
App Registration Settings:
├── Redirect URIs: https://app.dewey.app/auth/callback
├── API Permissions: Mail.Read, User.Read
├── Certificates & Secrets: Client secret or certificate
├── Token Configuration: Optional claims (tenant_id, email)
└── Enterprise App: Enable for SSO
```

### 2. Processing Pipeline

Async worker-based processing:

1. **Content Extraction** - Text normalization, OCR for attachments
2. **Campaign Detection** - Identify templated/coordinated messages
3. **AI Analysis** - Sentiment, entities, classification suggestions
4. **Workflow Execution** - Trigger automated actions

### 3. AI Provider Architecture

Pluggable interface supporting multiple providers:

```python
class AIProvider(Protocol):
    async def analyze(
        self,
        content: str,
        categories: list[Category],
        config: AnalysisConfig
    ) -> AnalysisResult:
        ...

# Implementations
class ClaudeProvider(AIProvider): ...
class OpenAIProvider(AIProvider): ...
class OllamaProvider(AIProvider): ...
```

### 4. Multi-Tenancy

-   Row-level security (tenant_id on all tables)
-   Per-tenant encryption keys (AWS KMS)
-   Tenant-specific AI provider configuration
-   Custom fields and categories per tenant

## Data Model Overview

```
Tenant (Organization)
├── Users
├── Categories (hierarchical)
├── Workflows
├── Custom Field Definitions
├── Forms
└── Messages
    ├── Analysis (AI results)
    ├── Contact (sender)
    ├── Campaign (if template match)
    └── Workflow Executions
```

Key entities:

-   **Message** - Email, form submission, or API-submitted content
-   **Contact** - Sender/constituent with custom field values
-   **Campaign** - Detected coordinated messaging campaigns
-   **Analysis** - AI-generated sentiment, entities, suggestions
-   **Workflow** - Automated actions triggered by conditions

## Deployment Architecture

### AWS Infrastructure

```
Route 53 (DNS)
    ↓
CloudFront (CDN) - Static assets
    ↓
Application Load Balancer
    ↓
┌─────────────────────────────────────────┐
│              ECS Fargate                │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ API Service │  │ Worker Service  │   │
│  │ (FastAPI)   │  │ (Queue Consumer)│   │
│  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│                 VPC                     │
│  RDS PostgreSQL │ ElastiCache │ SQS     │
│  (Multi-AZ)     │ (Redis)     │         │
└─────────────────────────────────────────┘
```

### FedRAMP Deployment

For government customers, separate deployment in AWS GovCloud:

-   Isolated VPC and infrastructure
-   FIPS 140-2 encryption
-   FedRAMP-authorized AI providers (Azure OpenAI Gov or self-hosted)
-   Enhanced audit logging (1+ year retention)

## Security

### Authentication

-   JWT tokens with tenant context (web UI)
-   API keys with scoped permissions (programmatic access)
-   SAML/OIDC SSO for enterprise

### API Keys & Service Credentials

Tenants can create API keys for programmatic access, enabling integration with external BI tools (Tableau, Power BI, Looker, custom dashboards).

**API Key Model:**

```python
class APIKey(SQLModel, table=True):
    id: UUID
    tenant_id: UUID                    # FK to tenant
    name: str                          # Human-readable name
    key_hash: str                      # SHA-256 hash (never store plaintext)
    key_prefix: str                    # First 8 chars for identification (e.g., "dwky_a1b2")
    scopes: list[str]                  # Permissions: ["read:messages", "read:analytics"]
    created_by: UUID                   # User who created the key
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None        # Optional expiration
    is_active: bool
    rate_limit: int                    # Requests per minute (default: 100)
    allowed_ips: list[str] | None      # Optional IP whitelist
```

**Available Scopes:**
| Scope | Access |
|-------|--------|
| `read:messages` | List and view messages |
| `read:contacts` | List and view contacts |
| `read:analytics` | Access analytics endpoints |
| `read:categories` | List categories |
| `write:messages` | Submit new messages |
| `write:contacts` | Create/update contacts |
| `admin` | Full access (tenant admin only) |

**API Key Authentication Flow:**

```
Client Request:
  Authorization: Bearer dwky_a1b2c3d4e5f6g7h8...

Server:
  1. Extract key from header
  2. Hash the key, lookup in database
  3. Verify: is_active, not expired, IP allowed
  4. Attach tenant context to request
  5. Check scopes against requested endpoint
  6. Update last_used_at
  7. Enforce rate limiting
```

**API Key Management Endpoints:**

```
POST   /api/v1/api-keys              # Create new key (returns plaintext ONCE)
GET    /api/v1/api-keys              # List keys (shows prefix only)
GET    /api/v1/api-keys/:id          # Get key details
PATCH  /api/v1/api-keys/:id          # Update (name, scopes, active, rate_limit)
DELETE /api/v1/api-keys/:id          # Revoke key
POST   /api/v1/api-keys/:id/rotate   # Rotate key (invalidate old, create new)
```

**BI Tool Integration Examples:**

_Tableau:_

```
Web Data Connector URL: https://api.dewey.app/v1/analytics/tableau
Authentication: API Key (Bearer token)
```

_Power BI:_

```
OData Feed: https://api.dewey.app/v1/odata/messages
Authentication: API Key header
```

_Direct API (Python):_

```python
import requests

response = requests.get(
    "https://api.dewey.app/v1/analytics/sentiment",
    headers={"Authorization": "Bearer dwky_your_api_key"},
    params={"start_date": "2024-01-01", "end_date": "2024-12-31"}
)
data = response.json()
```

### Power BI & Analytics Data Layer

Customers don't get direct database access. Instead, Dewey exposes a **curated analytics API** with pre-defined datasets optimized for BI tools.

**Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Power BI / Tableau / Looker                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │   OData      │   │   REST API   │   │  Export      │
    │   Endpoint   │   │   /analytics │   │  (CSV/Excel) │
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              ▼
    ┌────────────────────────────────────────────────────────────┐
    │                  Analytics Data Layer                      │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │              Curated Datasets (Views)               │   │
    │  ├─────────────────────────────────────────────────────┤   │
    │  │ • messages_summary    - Aggregated message data     │   │
    │  │ • sentiment_trends    - Sentiment over time         │   │
    │  │ • category_breakdown  - Messages by category        │   │
    │  │ • contact_analytics   - Contact engagement metrics  │   │
    │  │ • campaign_summary    - Coordinated campaigns       │   │
    │  │ • workflow_metrics    - Automation performance      │   │
    │  │ • custom_field_pivot  - Data by custom fields       │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                              │                             │
    │                    Row-Level Security                      │
    │                    (tenant_id filtering)                   │
    └──────────────────────────────┼─────────────────────────────┘
                                   ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  PostgreSQL Database                        │
    │                  (Raw tables - NOT exposed)                 │
    └─────────────────────────────────────────────────────────────┘
```

**Curated Datasets (Data Dictionary):**

| Dataset              | Description             | Key Fields                                                                                     |
| -------------------- | ----------------------- | ---------------------------------------------------------------------------------------------- |
| `messages_summary`   | Core message data       | id, received_at, source, sentiment_score, sentiment_label, categories, is_campaign, contact_id |
| `sentiment_trends`   | Daily/weekly aggregates | date, avg_sentiment, positive_count, negative_count, neutral_count, total_count                |
| `category_breakdown` | Messages by category    | category_id, category_name, message_count, avg_sentiment, period                               |
| `contact_analytics`  | Contact engagement      | contact_id, email, message_count, first_contact, last_contact, avg_sentiment, custom_fields    |
| `campaign_summary`   | Coordinated campaigns   | campaign_id, name, message_count, unique_senders, first_seen, last_seen, template_preview      |
| `workflow_metrics`   | Automation stats        | workflow_id, name, executions_count, success_rate, avg_duration                                |
| `custom_field_pivot` | Segment analysis        | field_name, field_value, message_count, avg_sentiment, category_distribution                   |

**What's Exposed vs Hidden:**

| Exposed to BI Tools      | Hidden from BI Tools     |
| ------------------------ | ------------------------ |
| Aggregated metrics       | Raw email body content   |
| Sentiment scores         | Full message text        |
| Category assignments     | PII beyond contact email |
| Custom field values      | Internal IDs             |
| Timestamps               | System metadata          |
| Contact engagement stats | AI raw responses         |

**OData Endpoint for Power BI:**

```
# Power BI connects to:
https://api.dewey.app/v1/odata/

# Available entity sets:
/odata/messages_summary
/odata/sentiment_trends
/odata/category_breakdown
/odata/contact_analytics
/odata/campaign_summary

# Supports:
- $filter (e.g., ?$filter=received_at ge 2024-01-01)
- $select (e.g., ?$select=id,sentiment_score,category)
- $orderby
- $top, $skip (pagination)
- $count
```

**Power BI Template:**

Provide customers a `.pbit` template file with:

-   Pre-configured OData connection
-   Standard dashboards (sentiment, volume, categories)
-   Parameters for date range, API key
-   Refresh schedule configuration

**Data Refresh Options:**
| Mode | Use Case | Latency |
|------|----------|---------|
| DirectQuery | Real-time dashboards | Live |
| Import (scheduled) | Historical analysis | 1-24 hours |
| Export (CSV/Excel) | Ad-hoc analysis | Manual |

**API Key Scopes for Analytics:**

```
read:analytics:basic     - Aggregated data only
read:analytics:detailed  - Include contact-level data
read:analytics:export    - Bulk export capability
```

### Authorization & Role-Based Access Control (RBAC)

Dewey implements a flexible RBAC system that can operate standalone or sync with Azure AD groups.

**Role Hierarchy:**
| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `owner` | Tenant owner | All permissions, billing, delete tenant |
| `admin` | Administrator | Manage users, settings, integrations, API keys |
| `manager` | Team manager | View all messages, manage categories, run reports |
| `agent` | Standard user | View/respond to assigned messages, use workflows |
| `viewer` | Read-only | View messages and analytics only |

**Permission Model:**

```python
class Role(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    name: str                          # "admin", "manager", or custom
    is_system: bool                    # True for built-in roles
    permissions: list[str]             # ["messages:read", "messages:write", ...]
    azure_ad_group_id: str | None      # Sync with Azure AD group

class UserRole(SQLModel, table=True):
    user_id: UUID
    role_id: UUID
    assigned_at: datetime
    assigned_by: UUID | None           # Who assigned this role

class User(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    email: str
    name: str
    azure_ad_oid: str | None           # Azure AD Object ID (for SSO users)
    is_active: bool
    last_login_at: datetime | None
```

**Available Permissions:**

```
# Messages
messages:read          - View messages
messages:write         - Create/update messages
messages:delete        - Delete messages
messages:assign        - Assign messages to users

# Contacts
contacts:read          - View contacts
contacts:write         - Create/update contacts
contacts:delete        - Delete contacts

# Categories
categories:read        - View categories
categories:write       - Create/update/delete categories

# Workflows
workflows:read         - View workflows
workflows:write        - Create/update workflows
workflows:execute      - Manually trigger workflows

# Analytics
analytics:read         - View dashboards and reports
analytics:export       - Export data

# Forms
forms:read             - View forms
forms:write            - Create/update forms

# Settings & Admin
settings:read          - View tenant settings
settings:write         - Modify tenant settings
users:read             - View users
users:write            - Invite/manage users
roles:write            - Create/modify roles
api_keys:manage        - Create/revoke API keys
integrations:manage    - Configure O365, webhooks, etc.
billing:manage         - View/modify subscription (owner only)
```

**Azure AD Group Sync:**

Roles can optionally be linked to Azure AD security groups for automatic provisioning:

```
┌────────────────────────────────────────────────────────────┐
│                    Azure AD                                │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Group:          │  │ Group:          │                  │
│  │ Dewey-Admins    │  │ Dewey-Agents    │                  │
│  │ (abc-123-...)   │  │ (def-456-...)   │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
└───────────┼─────────────────────┼──────────────────────────┘
            │                     │
            ▼                     ▼
┌────────────────────────────────────────────────────────────┐
│                      Dewey                                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Role: admin     │  │ Role: agent     │                  │
│  │ azure_ad_group: │  │ azure_ad_group: │                  │
│  │ abc-123-...     │  │ def-456-...     │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                            │
│  On SSO login:                                             │
│  1. Get user's group memberships from Graph API            │
│  2. Match groups to Dewey roles                            │
│  3. Auto-assign/remove roles based on group membership     │
└────────────────────────────────────────────────────────────┘
```

**Graph API for Group Sync:**

```
GET /me/memberOf
Authorization: Bearer {token}

Returns: List of groups/roles the user belongs to
Permission required: GroupMember.Read.All or Directory.Read.All
```

**Role Assignment Modes:**

1. **Manual only** - Admins assign roles in Dewey UI
2. **Azure AD sync** - Roles auto-assigned based on AD group membership
3. **Hybrid** - AD groups for base roles, manual for exceptions

**Permission Checking:**

```python
# In API endpoint
@require_permission("messages:write")
async def create_message(request: Request, data: MessageCreate):
    ...

# Or check programmatically
if not current_user.has_permission("analytics:export"):
    raise HTTPException(403, "Export permission required")
```

### Row-Level Security

-   All queries filtered by tenant_id
-   Message assignment filtering (agents see only assigned messages, managers see all)
-   API rate limiting per tenant and per API key

### Compliance

-   SOC 2 Type II (enterprise requirement)
-   GDPR data handling
-   FedRAMP Moderate (government customers)

## Scalability

| Scale      | Messages/Day | Infrastructure                      |
| ---------- | ------------ | ----------------------------------- |
| Startup    | < 10K        | Single region, 2 containers         |
| Growth     | 10K-100K     | Read replicas, auto-scaling workers |
| Enterprise | 100K+        | Multi-region, dedicated resources   |

## Testing Strategy

### Testing Pyramid

```
                    ┌─────────┐
                    │   E2E   │  Playwright - Critical user flows
                   ┌┴─────────┴┐
                   │Integration│  pytest + TestClient - API & DB
                  ┌┴───────────┴┐
                  │    Unit     │  pytest + Jest - Business logic
                  └─────────────┘
```

### Backend Testing (pytest)

| Test Type       | Tools                         | Coverage Target                    |
| --------------- | ----------------------------- | ---------------------------------- |
| **Unit**        | pytest, pytest-mock           | Models, services, utilities        |
| **Integration** | pytest, httpx, testcontainers | API endpoints, database operations |
| **Contract**    | pact-python                   | AI provider response contracts     |

**Example Unit Test:**

```python
# tests/unit/services/test_campaign_detection.py
def test_calculate_similarity_identical_content():
    service = CampaignDetectionService()
    score = service.calculate_similarity(
        "Please support bill HR-123",
        "Please support bill HR-123"
    )
    assert score == 1.0

def test_calculate_similarity_different_content():
    service = CampaignDetectionService()
    score = service.calculate_similarity(
        "Please support bill HR-123",
        "I oppose the new tax proposal"
    )
    assert score < 0.3
```

**Example Integration Test:**

```python
# tests/integration/api/test_messages.py
async def test_create_message_triggers_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict
):
    response = await client.post(
        "/api/v1/messages",
        json={"subject": "Feedback", "body_text": "Great service!"},
        headers=auth_headers
    )
    assert response.status_code == 201

    message_id = response.json()["id"]
    # Verify message queued for processing
    message = await db_session.get(Message, message_id)
    assert message.processing_status == "pending"
```

### Frontend Testing (Jest + Playwright)

| Test Type       | Tools                   | Coverage Target              |
| --------------- | ----------------------- | ---------------------------- |
| **Unit**        | Vitest, Testing Library | Hooks, utilities, components |
| **Integration** | Testing Library         | Component interactions       |
| **E2E**         | Playwright              | Critical user flows          |
| **Visual**      | Playwright screenshots  | UI regression                |

**Example Component Test:**

```typescript
// src/components/__tests__/SentimentBadge.test.tsx
describe('SentimentBadge', () => {
    it('renders positive sentiment correctly', () => {
        render(<SentimentBadge score={0.8} />);
        expect(screen.getByText('Positive')).toBeInTheDocument();
        expect(screen.getByTestId('badge')).toHaveClass('bg-green-100');
    });

    it('renders negative sentiment correctly', () => {
        render(<SentimentBadge score={-0.6} />);
        expect(screen.getByText('Negative')).toBeInTheDocument();
        expect(screen.getByTestId('badge')).toHaveClass('bg-red-100');
    });
});
```

**Example E2E Test:**

```typescript
// e2e/message-flow.spec.ts
test('submit form and view analysis', async ({ page }) => {
    // Submit a form
    await page.goto('/f/test-tenant/feedback-form');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="message"]', 'Excellent customer support!');
    await page.click('button[type="submit"]');
    await expect(page.locator('.success-message')).toBeVisible();

    // Login and view in dashboard
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@test-tenant.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');

    // Verify message appears with analysis
    await page.goto('/messages');
    await expect(page.locator('text=Excellent customer support')).toBeVisible();
    await expect(page.locator('[data-testid="sentiment-positive"]')).toBeVisible();
});
```

### Performance Testing (Locust)

```python
# tests/load/locustfile.py
class MessageIntakeUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def submit_message(self):
        self.client.post("/api/v1/messages", json={
            "subject": "Test message",
            "body_text": "This is a load test message",
            "sender_email": f"user{random.randint(1,1000)}@test.com"
        })

    @task(1)
    def list_messages(self):
        self.client.get("/api/v1/messages?limit=20")
```

### Test Database Strategy

-   **Unit tests**: Mock database calls
-   **Integration tests**: Testcontainers (ephemeral PostgreSQL)
-   **E2E tests**: Dedicated test database, reset between runs

### CI/CD Test Pipeline

```yaml
# .github/workflows/test.yml
jobs:
    test:
        steps:
            - name: Backend Unit Tests
              run: pytest tests/unit -v --cov=app

            - name: Backend Integration Tests
              run: pytest tests/integration -v
              env:
                  DATABASE_URL: postgresql://test@localhost/dewey_test

            - name: Frontend Unit Tests
              run: npm test -- --coverage

            - name: E2E Tests
              run: npx playwright test

            - name: Load Test (smoke)
              run: locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s
```

## Related Documentation

-   [TODO.md](./TODO.md) - Implementation checklist
-   [README.md](./README.md) - Installation and setup
-   [Full Design Document](./.claude/plans/sorted-riding-allen.md) - Detailed specifications
