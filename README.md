# Auth System

Production-ready authentication API built with FastAPI, SQLAlchemy, JWT, and PostgreSQL.

## Tech Stack

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.x (async) + asyncpg
- **Auth:** JWT access/refresh tokens, bcrypt, TOTP 2FA
- **Cache:** Redis (token blacklist, rate limiting, password reset, email verification)
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Runtime:** Python 3.14+

## Quick Start

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Copy env config
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
uv run alembic upgrade head

# Start server (development with auto-reload)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or start server (production)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Server starts at `http://localhost:8000`.

### Docker

```bash
# Start all services (app + Postgres + Redis)
docker compose up -d

# Run database migrations
docker compose exec app uv run alembic upgrade head

# View logs
docker compose logs -f app

# Stop everything
docker compose down
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/health` | Health check | None |
| POST | `/api/v1/auth/register` | Register user | Rate-limited (5/min) |
| POST | `/api/v1/auth/login` | Login (supports TOTP + backup code) | Rate-limited (10/min) |
| POST | `/api/v1/auth/refresh` | Refresh tokens | Rate-limited (10/min) |
| POST | `/api/v1/auth/logout` | Logout | Bearer |
| POST | `/api/v1/auth/forgot-password` | Request password reset | Rate-limited (3/5min) |
| POST | `/api/v1/auth/reset-password` | Reset password with token | None |
| GET | `/api/v1/auth/verify-email` | Verify email with token | None |
| POST | `/api/v1/auth/resend-verification` | Resend verification email | Rate-limited (3/5min) |
| POST | `/api/v1/auth/2fa/enable` | Enable TOTP 2FA (generates secret + backup codes) | Bearer |
| POST | `/api/v1/auth/2fa/verify` | Confirm 2FA setup with first TOTP code | Bearer |
| POST | `/api/v1/auth/2fa/disable` | Disable 2FA (requires password + TOTP/backup) | Bearer |
| GET | `/api/v1/auth/oauth/google` | Google OAuth URL | None |
| GET | `/api/v1/auth/oauth/google/callback` | Google OAuth callback | None |
| GET | `/api/v1/auth/oauth/github` | GitHub OAuth URL | None |
| GET | `/api/v1/auth/oauth/github/callback` | GitHub OAuth callback | None |
| GET | `/api/v1/auth/sessions` | List active sessions | Bearer |
| DELETE | `/api/v1/auth/sessions/{id}` | Revoke a specific session | Bearer |
| POST | `/api/v1/auth/sessions/revoke-others` | Revoke all sessions except current | Bearer |
| GET | `/api/v1/users/me` | Current user | Bearer |
| GET | `/api/v1/users` | List users | Admin |
| GET | `/api/v1/users/{id}` | Get user | Bearer |
| PATCH | `/api/v1/users/{id}` | Update user | Admin |
| DELETE | `/api/v1/users/{id}` | Deactivate user | Admin |

## Project Structure

```
app/
├── api/v1/        # Route handlers
├── core/          # Security, cache, rate limiting
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

1. `POST /auth/register` or `/auth/login` returns `access_token` (30min) + `refresh_token` (7 days)
2. Access token goes in `Authorization: Bearer <token>` header
3. When access expires, `POST /auth/refresh` with refresh token in body gets a new pair
4. `POST /auth/logout` revokes the refresh token server-side + blacklists the access JTI
5. `POST /auth/forgot-password` generates a reset token (stored in Redis, 15min TTL); returns token in body when `DEBUG=true`
6. `POST /auth/reset-password` accepts token + new password to change credentials
7. `POST /auth/login` accepts optional `totp_code` and `backup_code` fields when 2FA is enabled
8. OAuth (Google/GitHub): GET the auth URL, user authorizes, callback returns JWT tokens

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
| `APP_URL` | `http://localhost:8000` | Public URL (OAuth redirects) |
| `DEBUG` | `false` | Enable debug mode + /docs |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Lockout duration |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | Block login for unverified emails |
| `SMTP_HOST` | — | SMTP server for emails |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password |
| `SMTP_FROM_EMAIL` | — | From address for emails |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | — | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth client secret |

## Features

- User registration and login with bcrypt password hashing
- JWT access/refresh token pair with Redis blacklist
- Email verification flow (token in Redis, 24h TTL)
- Password reset flow (token in Redis, 15min TTL)
- TOTP 2FA with 10 single-use backup codes (bcrypt-hashed)
- Account lockout after N failed login attempts
- Redis-based rate limiting (sliding window)
- Google and GitHub OAuth login
- Session management (list, revoke, revoke-others)
- Role-based access control (admin/user)
- Docker compose (app + Postgres + Redis)
