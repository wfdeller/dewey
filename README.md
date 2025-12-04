# Dewey

> AI-Powered Communication Processing Platform

Dewey is a SaaS platform for processing incoming communications (emails, forms, documents) using AI to analyze sentiment, classify issues, and automate workflows.

## Features

-   **Multi-Channel Intake** - Email, web forms, API, webhooks
-   **AI Analysis** - Sentiment scoring, entity extraction, classification suggestions
-   **Campaign Detection** - Identify coordinated/templated message campaigns
-   **Contact Management** - Track sender history with custom fields
-   **Workflow Automation** - Rule-based triggers and automated actions
-   **Analytics Dashboard** - Real-time insights, trends, and reports
-   **Form Builder** - Create embeddable forms and surveys
-   **Multi-Tenant** - Isolated data with per-tenant configuration

## Target Users

-   **Companies** - Customer feedback processing
-   **Elected Officials** - Constituent correspondence management
-   **Government Agencies** - Public inquiry handling

## Documentation

-   [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
-   [TODO.md](./TODO.md) - Implementation checklist and progress tracking
-   [Design Document](./.claude/plans/sorted-riding-allen.md) - Detailed specifications

## Tech Stack

| Component  | Technology                         |
| ---------- | ---------------------------------- |
| Backend    | Python 3.11+ / FastAPI             |
| ORM        | SQLModel + Alembic                 |
| Frontend   | TypeScript / React / Vite          |
| UI Library | Ant Design 5.x                     |
| Database   | PostgreSQL 15+                     |
| Cache      | Redis 7+                           |
| Queue      | AWS SQS / Redis Streams            |
| AI         | Claude, OpenAI, Ollama (pluggable) |
| Testing    | pytest, Playwright, Locust         |

## Prerequisites

-   Python 3.11+
-   Node.js 20+
-   Docker and Docker Compose
-   PostgreSQL 15+ (or use Docker)
-   Redis 7+ (or use Docker)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/dewey.git
cd dewey
```

### 2. Environment Setup

```bash
# Copy example environment file
cd backend
cp .env.example .env
cd ../frontend
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, REDIS_URL, AI provider keys
```

### 3. Start Infrastructure (Docker)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip3 install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 6. Access the Application

-   **Frontend**: http://localhost:5173
-   **API**: http://localhost:8000
-   **API Docs**: http://localhost:8000/docs

## Docker Compose (Full Stack)

For a complete local environment:

```bash
docker-compose up -d
```

This starts:

-   PostgreSQL (port 5432)
-   Redis (port 6379)
-   Backend API (port 8000)
-   Frontend (port 5173)
-   Worker (background processing)

## Configuration

### Environment Variables

| Variable                | Description                         | Required                |
| ----------------------- | ----------------------------------- | ----------------------- |
| `DATABASE_URL`          | PostgreSQL connection string        | Yes                     |
| `REDIS_URL`             | Redis connection string             | Yes                     |
| `SECRET_KEY`            | JWT signing + tenant key encryption | Yes (min 32 chars)      |
| `ANTHROPIC_API_KEY`     | Claude API key (platform/Free tier) | For Free tier w/ Claude |
| `OPENAI_API_KEY`        | OpenAI API key (platform/Free tier) | For Free tier w/ OpenAI |
| `AZURE_CLIENT_ID`       | Azure AD app client ID              | For Azure AD SSO        |
| `AZURE_CLIENT_SECRET`   | Azure AD app client secret          | For Azure AD SSO        |
| `AZURE_TENANT_ID`       | Azure AD tenant ID (or "common")    | For Azure AD SSO        |
| `AZURE_REDIRECT_URI`    | OAuth callback URL                  | For Azure AD SSO        |
| `AWS_REGION`            | AWS region for SQS                  | For production          |
| `AWS_ACCESS_KEY_ID`     | AWS credentials                     | For production          |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials                     | For production          |

### AI Provider Configuration

Dewey supports multiple AI providers with a tiered key management model:

**Key Sources:**

-   **Platform Keys** (Free/Trial tiers): Uses shared API keys from environment variables
-   **Tenant Keys** (Pro/Enterprise tiers): Customers provide their own API keys, stored encrypted per-tenant

**Environment Variables** (Platform Keys Only):

```env
# Default AI provider (claude, openai, azure_openai, ollama)
DEFAULT_AI_PROVIDER=claude

# Platform keys - used ONLY for Free/Trial tenants
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# For Ollama (self-hosted, no API key needed)
OLLAMA_BASE_URL=http://localhost:11434
```

**For Pro/Enterprise Tenants:**
Customers configure their own API keys in the admin console. Keys are encrypted at rest using Fernet symmetric encryption derived from `SECRET_KEY`.

This separation ensures:

-   Data isolation (AI provider logs are tenant-specific)
-   Usage attribution (customers see their own usage in provider dashboards)
-   Compliance (no cross-tenant data exposure via AI APIs)

## Project Structure

```
dewey/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Config, security, database
│   │   ├── models/       # SQLModel models
│   │   ├── services/     # Business logic
│   │   └── workers/      # Background processors
│   ├── tests/
│   │   ├── unit/         # Unit tests (pytest)
│   │   ├── integration/  # Integration tests
│   │   └── load/         # Load tests (Locust)
│   ├── alembic/          # Database migrations
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── services/
│   ├── e2e/              # Playwright E2E tests
│   └── package.json
├── infrastructure/
│   ├── terraform/        # IaC for AWS
│   └── docker-compose.yml
├── ARCHITECTURE.md
├── TODO.md
└── README.md
```

## Development

### Running Tests

```bash
# Backend unit tests
cd backend
pytest tests/unit -v

# Backend integration tests (requires PostgreSQL)
pytest tests/integration -v

# Backend with coverage
pytest --cov=app --cov-report=html

# Frontend unit tests
cd frontend
npm test

# E2E tests
npx playwright test

# Load tests (10 users, 30 seconds)
cd backend
locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s
```

### Code Quality

```bash
# Backend linting and formatting
cd backend
ruff check .
black .
mypy .

# Frontend linting
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### AWS (Production)

See `infrastructure/terraform/` for infrastructure-as-code:

```bash
cd infrastructure/terraform/environments/production
terraform init
terraform plan
terraform apply
```

### Docker (Self-Hosted)

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## API Reference

API documentation is auto-generated from OpenAPI spec:

-   **Swagger UI**: http://localhost:8000/docs
-   **ReDoc**: http://localhost:8000/redoc
-   **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Endpoint                         | Description                   |
| -------------------------------- | ----------------------------- |
| `POST /api/v1/auth/register`     | Register new user and tenant  |
| `POST /api/v1/auth/login`        | Login with email/password     |
| `POST /api/v1/auth/refresh`      | Refresh access token          |
| `GET /api/v1/auth/me`            | Get current user info         |
| `GET /api/v1/auth/azure/login`   | Get Azure AD authorization URL|
| `GET /api/v1/auth/azure/callback`| Azure AD OAuth callback       |
| `POST /api/v1/messages`          | Submit message via API        |
| `GET /api/v1/messages`           | List messages with filters    |
| `GET /api/v1/analytics/*`        | Analytics data                |
| `POST /api/v1/forms/{id}/submit` | Form submission               |

## Cloud Marketplace

Dewey is available on:

-   **Azure Marketplace** (Primary) - [Link TBD]
-   **AWS Marketplace** - [Link TBD]

## Authentication

Dewey supports two authentication methods:

### Password Authentication
Standard email/password authentication with JWT tokens.

```bash
# Register a new tenant and user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepass123", "name": "Admin User", "tenant_name": "My Company", "tenant_slug": "my-company"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepass123"}'

# Use the access token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Azure AD SSO (OpenID Connect)
Enterprise SSO via Microsoft Azure Active Directory. See [.env.example](./backend/.env.example) for Azure AD configuration.

1. Register an app in Azure Portal > App registrations
2. Configure redirect URI: `http://localhost:8000/api/v1/auth/azure/callback`
3. Add API permissions: `openid`, `profile`, `email`, `User.Read`
4. Set environment variables: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`

```bash
# Get Azure AD login URL
curl http://localhost:8000/api/v1/auth/azure/login

# Frontend redirects user to auth_url, then handles callback
```

## Microsoft 365 Integration

Dewey integrates natively with Microsoft 365 for email intake:

1. **Admin Consent**: Tenant admin grants Dewey access to read mail
2. **Mailbox Configuration**: Select shared mailbox(es) to monitor
3. **Real-time Sync**: New emails flow into Dewey via Graph API webhooks
4. **Azure AD SSO**: Users sign in with their Microsoft accounts

Required Graph API permissions: `Mail.Read`, `User.Read`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[License TBD]

## Support

-   **Documentation**: See [ARCHITECTURE.md](./ARCHITECTURE.md) and [TODO.md](./TODO.md)
-   **Issues**: [GitHub Issues](https://github.com/your-org/dewey/issues)
-   **Email**: support@dewey.app
