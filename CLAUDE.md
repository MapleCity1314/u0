# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

u0 is a real-time fund analysis and quantitative research platform that provides T+0 fund NAV estimation using factor regression models. The platform combines AI-powered analysis with financial data to eliminate information lag in fund investing.

**Core Philosophy**: `labs` (exploration) → `core` (abstraction) → `services` (service layer) → `apps` (product)

## Architecture

### Monorepo Structure

```
u0/
├── apps/web/          # Next.js 16 frontend (React 19)
├── services/          # Python FastAPI backend services
├── core/              # Shared auth & database layer
├── labs/              # Experimental models (research prototypes)
├── models/            # Shared data models
└── data/              # Data processing utilities
```

### Frontend (apps/web)

- **Framework**: Next.js 16.1.6 with App Router, React 19.2.3
- **Styling**: Tailwind CSS 4.1.18
- **State**: Zustand 4.5.7
- **AI**: Vercel AI SDK (`@ai-sdk/react`)
- **UI**: Radix UI + custom components in `components/ui/`

**Route Groups**:
- `(auth)/` - Public routes: login, register, auth API routes
- `(dashboard)/` - Protected routes: search, chat, news, positions, watchlist

**Auth Pattern**: Next.js API routes proxy to Python backend. Token encryption/decryption in `app/(auth)/api/auth/_crypto.ts`. Cookie-based sessions with `AUTH_COOKIE_NAME`.

### Backend (services/)

**Main Entry Points**:
- `services.server.main:app` - Aggregated service (all modules)
- `services.fund_nav.app:app` - Standalone fund NAV service

**Service Modules**:
- `fund_nav/` - Fund NAV estimation, search, curve, returns (uses AKShare API)
- `users/` - Auth, user management, positions, watchlist
- `news/` - News aggregation with background collection tasks
- `agent/` - AI agent system (experimental, includes MCP support)

**Module Registration**: Services use `module.py` + `registry.py` pattern for dynamic loading into main app.

**Data Layer**:
- PostgreSQL with SQLAlchemy ORM
- Alembic migrations in `services/migrations/`
- Core models: User, SessionToken, WatchlistItem, Position, PositionEvent, Invite
- Connection: `postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/u0`

**Caching**:
- Redis cache via `services/modules/redis_cache/client.py` (if `REDIS_URL` set)
- AKShare API wrapper with TTL cache in `services/modules/akshare/cache.py`
- Fund estimate/curve responses are cached

## Development Commands

### Backend Services

```bash
# Run main aggregated service (all modules)
make service
# or: uvicorn services.server.main:app --reload

# Run standalone fund NAV service
make service-fund-nav
# or: uvicorn services.fund_nav.app:app --reload
```

### Frontend

```bash
# Development server
make web-dev
# or: cd apps/web && pnpm dev

# Production build
make web-build
# or: cd apps/web && pnpm build

# Start production server
make web-start
# or: cd apps/web && pnpm start
```

### Labs (Research Prototypes)

```bash
# Run specific fund estimation experiment
make lab-fund-nav
# or: python labs/fund_nav_rt_022485/main.py

# Run multi-fund holdings experiment
make lab-fund-nav-holdings
# or: python labs/fund_nav_multi_rt_holdings_20260202/main.py

# Run data sources experiment
make lab-data-sources
# or: python labs/fund_nav_data_sources_20260202/main.py
```

### Database Migrations

```bash
# Create new migration
cd services && alembic revision --autogenerate -m "description"

# Apply migrations
cd services && alembic upgrade head

# Rollback
cd services && alembic downgrade -1
```

## Key Integration Points

1. **Frontend → Backend**: Next.js API routes in `apps/web/app/(dashboard)/api/` proxy to Python FastAPI services
2. **Auth Flow**: Login → Python backend generates token → Next.js encrypts token → stores in cookie → validates on protected routes
3. **Data Sources**: AKShare API (Chinese financial data) → cached in Redis/memory → served via FastAPI → consumed by Next.js
4. **AI Chat**: Vercel AI SDK in frontend → calls `/api/chat` → uses agent system in `services/agent/`

## API Reference

Base URL: `http://localhost:8000`

Protected endpoints require: `Authorization: Bearer <token>`

**Key Endpoints**:
- `GET /api/funds/search?q=` - Search funds
- `GET /api/funds/{code}?source=auto|eastmoney|model|both` - Fund estimate detail
- `GET /api/funds/{code}/curve?days=` - NAV curve with estimate
- `GET /api/news?q=&market=&limit=&cursor=` - News list (full-text search)
- `POST /api/auth/register` - Register with invite code
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Current user (protected)
- `GET /api/positions` - List positions (protected)
- `POST /api/positions` - Create/update position (protected)
- `GET /api/watchlist` - List watchlist (protected)

**Pagination**: Use `cursor` (last item `id` from previous page). API returns items with `id < cursor`.

## Important Patterns

1. **Labs-First Development**: New models/strategies start in `labs/`, graduate to `services/` after validation
2. **Module System**: Services register via `module.py` with `register_module(app)` function
3. **Caching Strategy**: Redis if available, fallback to in-memory TTL cache
4. **Auth Security**: Passwords hashed with bcrypt, tokens are random 32-byte hex strings, sessions have expiration
5. **Audit Trail**: Position changes logged to `PositionEvent` table
6. **Error Handling**: Services return structured error responses with detail messages

## Environment Variables

Key variables (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection (optional, falls back to in-memory)
- `AUTH_SECRET` - Token encryption key (Next.js)
- `NEXT_PUBLIC_API_BASE` - Backend API base URL
- `CORS_ORIGINS` - Allowed CORS origins for backend

## Status

Project is in **early-stage MVP**. All fund estimates are for research purposes only, not investment advice.
