# Deployment Guide

> **Last updated:** May 13, 2026
> **Target:** Render (backend) + Vercel (frontend)

---

## 1. Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Vercel    │────▶│    Render    │────▶│  Supabase  │
│  (Frontend) │     │  (Backend)   │     │ (PostgreSQL)│
└─────────────┘     └──────────────┘     └────────────┘
```

- **Frontend** (React + Vite) is deployed to Vercel
- **Backend** (FastAPI) is deployed to Render as a Web Service
- **Database** is Supabase PostgreSQL
- In production, FastAPI also serves the built frontend from `backend/frontend/dist/`

---

## 2. Backend Deployment (Render)

### 2.1 Prerequisites

- Render account
- Supabase PostgreSQL database
- Git repository connected to Render

### 2.2 Render Web Service Configuration

| Setting | Value |
|---------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

### 2.3 Environment Variables

```env
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
SECRET_KEY=<production-secret-key>
ALLOWED_ORIGINS=https://hospital-management-system-nine-topaz.vercel.app
REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY=true
```

**Critical production settings:**
- `SECRET_KEY` must not be the dev fallback
- `DATABASE_URL` must not use SQLite
- `REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY` should be `true`
- `ALLOWED_ORIGINS` must explicitly list allowed origins (no wildcard for credentialed requests)

### 2.4 Database Migrations

Render runs migrations automatically via the build command. The migration command is included in the build step:

```bash
alembic upgrade head
```

**Important:** Migrations must be **idempotent** — safe to re-run. Use `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` patterns.

### 2.5 Cold Start Safety

- `ensure_default_tenant_exists()` is idempotent and runs at startup
- Database connection validation happens in the lifespan handler, not in request handlers
- Connection pooling is configured with `pool_pre_ping=True`

---

## 3. Frontend Deployment (Vercel)

### 3.1 Vercel Project Configuration

| Setting | Value |
|---------|-------|
| **Framework** | Vite |
| **Root Directory** | `backend/frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Node Version** | 20.x |

### 3.2 Environment Variables

```env
VITE_API_URL=https://your-render-app.onrender.com/api/v1
```

### 3.3 vercel.json

Create `backend/frontend/vercel.json`:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

This ensures client-side routing works correctly (all paths serve `index.html`).

---

## 4. Production Frontend Origin

The production frontend is hosted at:

```
https://hospital-management-system-nine-topaz.vercel.app
```

This origin must be listed in `ALLOWED_ORIGINS` on the backend.

---

## 5. CORS Configuration

```python
# app/core/config.py
ALLOWED_ORIGINS: list[str] = [
    "https://hospital-management-system-nine-topaz.vercel.app",
    "http://localhost:5173",  # dev
    "http://127.0.0.1:5173",  # dev
]
```

**Rules:**
- Wildcard (`*`) is NOT allowed for credentialed requests
- Each origin must be explicitly listed
- Dev origins are included for local testing

---

## 6. Build Verification

### 6.1 Local Build Check

Always verify the build locally before deploying:

```bash
# Backend
cd backend
alembic upgrade head
python -m pytest tests/ -v

# Frontend
cd backend/frontend
npm run build
npx tsc --noEmit
```

### 6.2 Common Build Issues

| Issue | Solution |
|-------|----------|
| TypeScript errors | Run `npx tsc --noEmit` and fix all errors |
| Missing environment variables | Check `.env` / `.env.local` configuration |
| Migration conflicts | Run `alembic check` to detect inconsistencies |
| CORS errors | Verify `ALLOWED_ORIGINS` includes the frontend origin |

---

## 7. Production Checklist

- [ ] `SECRET_KEY` is a strong, unique value (not the dev default)
- [ ] `DATABASE_URL` points to production PostgreSQL (not SQLite)
- [ ] `ALLOWED_ORIGINS` includes the production frontend URL
- [ ] `REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY` is `true`
- [ ] All migrations have been applied (`alembic upgrade head`)
- [ ] Backend health check passes (`GET /health`)
- [ ] Frontend build succeeds (`npm run build`)
- [ ] CORS is configured correctly
- [ ] Database connection pooling is configured
- [ ] `ensure_default_tenant_exists()` is idempotent

---

## 8. Rollback Strategy

### Database Rollback

```bash
# Check current migration
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Application Rollback

- Render: Deploy previous version from the Render dashboard
- Vercel: Use Vercel's instant rollback feature

---

## 9. Monitoring

- **Backend logs**: Render dashboard → Logs
- **Frontend analytics**: Vercel dashboard → Analytics
- **Database**: Supabase dashboard → Database → Monitoring
- **Health check**: `GET /health` endpoint
- **API health**: `GET /api/v1/health` endpoint

---

## 10. Related Documents

- `docs/ARCHITECTURE.md` — System architecture
- `docs/MIGRATION_GUIDE.md` — Migration governance
- `docs/API_CONVENTIONS.md` — API patterns
- `PRODUCTION_FIXES.md` — Production issue tracking
- `DEPLOYMENT.md` (root) — Original deployment notes
