# Auth System

Production-ready authentication API built with FastAPI, SQLAlchemy, JWT, and PostgreSQL.

## Tech Stack

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.x (async) + asyncpg
- **Auth:** JWT access/refresh tokens, bcrypt
- **Cache:** Redis (token blacklist)
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Runtime:** Python 3.13+

## Quick Start

```bash
# Install dependencies
uv sync

# Copy env config
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/health` | Health check | None |
| POST | `/api/v1/auth/register` | Register user | None |
| POST | `/api/v1/auth/login` | Login | None |
| POST | `/api/v1/auth/refresh` | Refresh tokens | None |
| POST | `/api/v1/auth/logout` | Logout | Bearer |
| GET | `/api/v1/users/me` | Current user | Bearer |
| GET | `/api/v1/users` | List users | Admin |
| GET | `/api/v1/users/{id}` | Get user | Bearer |
| PATCH | `/api/v1/users/{id}` | Update user | Admin |
| DELETE | `/api/v1/users/{id}` | Deactivate user | Admin |

## Project Structure

```
app/
├── api/v1/        # Route handlers
├── core/          # Security, cache utilities
├── models/        # SQLAlchemy ORM models
├── schemas/       # Pydantic request/response schemas
├── services/      # Business logic layer
├── config.py      # Environment config
├── database.py    # Async engine & session
├── dependencies.py# FastAPI dependencies
├── exceptions.py  # Custom HTTP exceptions
└── main.py        # App entry point
```

## Auth Flow

1. `POST /auth/register` or `/auth/login` returns `access_token` (15min) + `refresh_token` (7 days)
2. Access token goes in `Authorization: Bearer <token>` header
3. When access expires, `POST /auth/refresh` with refresh token in body gets a new pair
4. `POST /auth/logout` revokes the refresh token server-side

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | — | JWT signing key |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed origins |
| `DEBUG` | `false` | Enable debug mode |
