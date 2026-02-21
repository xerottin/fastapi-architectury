# FastAPI Architectury

A production-ready FastAPI backend built with a focus on **clean architecture**, **scalability**, and **separation of concerns**. This project serves as a reference implementation demonstrating how to structure a modern Python backend with multiple databases, async processing, file storage, and background task execution.

Architecture is the backbone of this project. Every layer has a clear responsibility, dependencies flow inward, and the system is designed to scale horizontally without rewriting core logic.

---

## Architecture

### Approach: Layered Architecture with Vertical Slicing

The project follows a **Layered Architecture** pattern combined with **vertical domain slicing**. Each domain module (User, Project, File) contains its own API routes, schemas, services, and models, while shared infrastructure lives in dedicated layers.

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI Routes)       │  Handles HTTP, validation, serialization
├─────────────────────────────────────────┤
│       Auth & Dependency Injection       │  JWT verification, DI providers
├─────────────────────────────────────────┤
│         Service / Business Logic        │  Domain rules, orchestration
├─────────────────────────────────────────┤
│           Models & Schemas              │  ORM models, Pydantic DTOs
├─────────────────────────────────────────┤
│         Infrastructure / Data Access    │  PostgreSQL, MongoDB, Redis, MinIO
└─────────────────────────────────────────┘
```

### Principles

- **SOLID** — single responsibility per module, dependency inversion via `Depends()`
- **Separation of Concerns** — routes never touch the database directly; services never know about HTTP
- **Dependency Inversion** — upper layers depend on abstractions, not concrete implementations
- **Async-first** — all I/O operations use async drivers (`asyncpg`, `motor`, async Redis)
- **Graceful Degradation** — non-critical services (MinIO, MongoDB) can fail without crashing the app

### Why This Architecture Scales

Each domain module is self-contained. Adding a new module means creating a new set of routes, schemas, services, and models — without touching existing code. Services can be extracted into standalone microservices by swapping the in-process call with an HTTP/gRPC client. The infrastructure layer is already decoupled from business logic, so switching from PostgreSQL to another database requires changes only in the data access layer.

---

## Tech Stack

| Technology       | Purpose                                      |
|------------------|----------------------------------------------|
| **FastAPI**      | Async web framework, OpenAPI docs generation |
| **PostgreSQL 16**| Primary relational database                  |
| **SQLAlchemy 2** | Async ORM with type-safe mapped columns      |
| **Alembic**      | Database schema migrations                   |
| **MongoDB 7**    | Document storage for flexible data           |
| **Motor**        | Async MongoDB driver                         |
| **Redis 7**      | Caching, session storage, Celery backend     |
| **RabbitMQ 3**   | Message broker for Celery tasks              |
| **Celery**       | Distributed background task queue            |
| **MinIO**        | S3-compatible object/file storage            |
| **Pydantic v2**  | Request/response validation & settings       |
| **JWT (jose)**   | Token-based authentication                   |
| **bcrypt**       | Password hashing                             |
| **Sentry**       | Error monitoring & performance tracking      |
| **Gunicorn**     | Production ASGI server with Uvicorn workers  |
| **Docker**       | Containerized deployment                     |

---

## Project Structure

```
app/
├── main.py                      # Application entry point, lifespan, middleware
├── Dockerfile                   # Container image definition
├── alembic.ini                  # Migration configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Dev/test dependencies
│
├── api/                         # API layer — HTTP endpoints
│   └── v1/
│       ├── user.py              # User CRUD & auth endpoints
│       ├── project.py           # Project management endpoints
│       ├── file.py              # File upload/download endpoints
│       └── mongo_test.py        # MongoDB integration endpoints
│
├── auth/                        # Authentication module
│   ├── jwt.py                   # Token creation & verification
│   └── dependencies.py          # Auth dependency (get_current_user)
│
├── core/                        # Application core
│   ├── config.py                # Settings via pydantic-settings
│   ├── exceptions.py            # Custom exception classes
│   └── dependencies.py          # Shared DI providers
│
├── models/                      # SQLAlchemy ORM models
│   ├── base.py                  # Abstract base (id, public_id, timestamps)
│   ├── user.py                  # User model
│   └── project.py               # Project model
│
├── schemas/                     # Pydantic request/response DTOs
│   ├── user.py                  # User schemas with validators
│   └── project.py               # Project schemas
│
├── services/                    # Business logic layer
│   ├── base.py                  # Shared service utilities
│   ├── user.py                  # User service (register, login, CRUD)
│   └── project.py               # Project service (CRUD, ownership)
│
├── db/                          # Data access & infrastructure
│   ├── base.py                  # SQLAlchemy declarative base
│   ├── session.py               # Async/sync session factories
│   └── clients/
│       ├── mongo.py             # MongoDB async client
│       ├── redis.py             # Redis async client
│       └── minio.py             # MinIO file storage service
│
├── worker/                      # Celery background tasks
│   ├── celery_app.py            # Celery configuration & beat schedule
│   └── my_task.py               # Task definitions
│
└── migrations/                  # Alembic migration scripts
    ├── env.py
    └── versions/
```

```
# Root level
├── docker-compose.yml           # Full stack (app + all services)
├── docker-compose.dev.yml       # Dev mode (services only, app runs locally)
└── example.env                  # Environment variable template
```

---

## How to Run the Project

### Requirements

- Docker & Docker Compose
- Python 3.12+ (for local development)

### Run with Docker (full stack)

```bash
# Clone the repository
git clone https://github.com/your-username/FastAPI-architectury.git
cd FastAPI-architectury

# Copy and configure environment variables
cp example.env app/.env
# Edit app/.env with your values

# Start all services
docker compose up --build -d

# The API is available at http://localhost:8008
# Swagger docs at http://localhost:8008/docs
```

### Run locally (development)

```bash
# Start infrastructure services only
docker compose -f docker-compose.dev.yml up -d

# Set up Python environment
cd app
python -m venv venv
source venv/bin/activate        # Linux/macOS
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp ../example.env .env
# Edit .env — set DB_HOST=localhost, MONGO_URI with localhost, etc.

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

```env
# Application
APP_NAME=Zehn-Arch
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=local                # local | production

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080
JWT_REFRESH_TOKEN_EXPIRE_HOURS=168

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your-password
DB_NAME=zehn_architectury

# MongoDB
MONGO_URI=mongodb://root:example@localhost:27049/admin
MONGO_DB_NAME=zehn_architectury

# Redis
REDIS_URL=redis://localhost:6379

# MinIO (S3-compatible storage)
MINIO_ENDPOINT=localhost:9222
MINIO_PUBLIC_URL=http://localhost:9222
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=minio-bucket

# Celery
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379

# Monitoring
SENTRY_DSN=                      # Optional, for production
```

### Docker Services & Ports

| Service    | Internal Port | External Port | Management UI          |
|------------|---------------|---------------|------------------------|
| FastAPI    | 8000          | 8008          | `/docs`                |
| PostgreSQL | 5432          | 5438          | —                      |
| MongoDB    | 27017         | 27049         | —                      |
| Redis      | 6379          | 6379          | —                      |
| RabbitMQ   | 5672          | 5672          | `localhost:15672`      |
| MinIO API  | 9000          | 9222          | —                      |
| MinIO Console | 9001       | 9211          | `localhost:9211`       |

---

## Core Features

### Authentication

JWT-based authentication with access and refresh tokens. Passwords are hashed with bcrypt. Protected endpoints use the `get_current_user` dependency.

```
POST /api/v1/users          → Register (returns tokens)
POST /api/v1/users/login    → Login (returns tokens)
GET  /api/v1/users/me       → Get current user (requires Bearer token)
```

### User Management

Full CRUD with soft deletes (`is_active` flag). Users are identified externally by `public_id` (UUID), not by auto-increment `id`.

### Project Management

CRUD operations with ownership tracking. A user can own multiple projects and be assigned to one project.

```
POST   /api/v1/project          → Create project
GET    /api/v1/project/list     → List user's projects
GET    /api/v1/project/my       → Get assigned project
GET    /api/v1/project/{id}     → Get project by ID
PATCH  /api/v1/project/{id}     → Update project
DELETE /api/v1/project/{id}     → Soft delete project
```

### File Storage

S3-compatible file management via MinIO with validation for MIME types and file sizes (max 10 MB, images only).

```
POST   /api/v1/file/upload              → Upload single file
POST   /api/v1/file/upload/multiple     → Upload multiple files
GET    /api/v1/file/                    → List files
GET    /api/v1/file/download/{name}     → Download file
GET    /api/v1/file/url/{name}          → Get presigned URL
DELETE /api/v1/file/{name}              → Delete file
```

### Request Flow

```
HTTP Request
  → Middleware (request ID, logging, CORS, compression)
    → FastAPI Router
      → Dependency Injection (auth, DB session)
        → Service Layer (business logic, validation)
          → ORM Model / DB Client
            → Database (PostgreSQL / MongoDB / Redis)
              → Response serialized via Pydantic schema
```

### Error Handling

Custom `AppException` with structured error responses and i18n support:

```json
{
  "error": {
    "code": "EMAIL_ALREADY_REGISTERED",
    "i18n_key": "errors.EMAIL_ALREADY_REGISTERED",
    "params": {},
    "message": "Email already registered"
  },
  "request_id": "a1b2c3d4-..."
}
```

Every request gets a unique `request_id` (returned in `X-Request-ID` header) for tracing through logs and Sentry.

### Validation

Pydantic v2 with field-level and model-level validators:

```python
class UserRegisterRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided")
        return self
```

### Database Layer

- **PostgreSQL** — primary storage via SQLAlchemy 2 async ORM with connection pooling
- **MongoDB** — document storage via Motor async driver (pool: 1–50 connections)
- **Redis** — caching and Celery result backend
- **Alembic** — automatic schema migrations, run on startup in Docker

All models inherit from a shared `BaseModel` providing `id`, `public_id` (UUID), `created_at`, `updated_at`, and `is_active` fields.

---

## Development

### Dev Mode

```bash
# Start infrastructure
docker compose -f docker-compose.dev.yml up -d

# Run app with hot reload
cd app
uvicorn main:app --reload --port 8000
```

### Run Tests

```bash
cd app
pytest
pytest --cov=. --cov-report=term-missing    # With coverage
pytest -x -v                                 # Stop on first failure
```

### Code Quality

```bash
black .                  # Format code
isort .                  # Sort imports
ruff check .             # Lint
mypy .                   # Type checking
```

### Adding a New Module

1. **Model** — create `models/order.py` with SQLAlchemy model inheriting from `BaseModel`
2. **Schema** — create `schemas/order.py` with Pydantic request/response DTOs
3. **Service** — create `services/order.py` with business logic functions
4. **Route** — create `api/v1/order.py` with FastAPI router
5. **Register** — add `include_router(order.router, prefix="/order")` in `api/v1/__init__.py`
6. **Migrate** — run `alembic revision --autogenerate -m "add order table" && alembic upgrade head`

Each step is isolated. The new module won't affect existing ones.

---

## Scalability & Best Practices

### Horizontal Scaling

- **Stateless API** — no server-side sessions; JWT tokens carry auth state. Add more Gunicorn workers or container replicas behind a load balancer.
- **Connection Pooling** — SQLAlchemy and Motor manage database connection pools. Each instance handles its own pool.
- **Background Tasks** — Celery workers scale independently. Add more workers to process tasks faster.

### Where to Add Microservices

Each domain module (User, Project, File) is a candidate for extraction:

```
Monolith                    Microservices
┌──────────┐               ┌──────────────┐
│ User     │    ──────→    │ User Service  │  (own DB, own deployment)
│ Project  │    ──────→    │ Project Svc   │
│ File     │    ──────→    │ File Svc      │
└──────────┘               └──────────────┘
```

Replace in-process service calls with HTTP/gRPC clients. RabbitMQ is already in place for async communication.

### Where to Add Caching

- **Redis is already connected.** Add caching at the service layer:
  - User profile lookups → cache by `public_id` with TTL
  - Project lists → cache per user with invalidation on write
  - File metadata → cache presigned URLs until expiry

### Where to Add Task Queues

Celery with RabbitMQ is already configured. Use it for:
- Image processing after upload (resize, thumbnail generation)
- Email notifications (welcome, password reset)
- Data aggregation and reports
- Scheduled cleanup jobs (already has beat schedule)

---

## Future Improvements

- **Role-Based Access Control (RBAC)** — granular permissions beyond basic roles
- **Rate Limiting** — per-user/per-endpoint throttling (settings already defined)
- **WebSocket Support** — real-time notifications and updates
- **API Versioning Strategy** — v2 routes alongside v1 with deprecation
- **Comprehensive Test Suite** — unit, integration, and e2e tests with async fixtures
- **CI/CD Pipeline** — GitHub Actions for lint, test, build, and deploy
- **OpenTelemetry** — distributed tracing across services
- **Database Read Replicas** — separate read/write connections for high-load scenarios
- **Event Sourcing** — audit trail for critical domain events
- **API Gateway** — centralized routing, auth, and rate limiting for microservice extraction

---

## License

This project is open source and available under the [MIT License](LICENSE).
