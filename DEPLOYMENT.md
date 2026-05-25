# Hospital Management System - Deployment Guide

> **See also:** `docs/DEPLOYMENT.md` for the canonical deployment documentation.

## 🚀 Deployment Overview

- **Backend**: Render / Railway (FastAPI)
- **Frontend**: Vercel (React + Vite)
- **Database**: Supabase (PostgreSQL)

---

## 📋 Prerequisites

1. Supabase project with PostgreSQL database
2. Render or Railway account for backend
3. Vercel account for frontend
4. Environment variables configured

---

## 🔧 Backend deployment (Render)

This repository intentionally does **not** ship a Render Blueprint (`render.yaml`) or any other in-repo Render service definition. The GitHub Actions workflow runs tests only and does not deploy or call the Render API. Deploys should attach only to your **existing** Render Web Service.

1. In the Render dashboard, open your single production Web Service (avoid creating an additional Web Service for this app unless you are deliberately replacing or migrating it).
2. Under **Settings**, connect this GitHub repository if needed and set **Root Directory** to `backend`.
3. **Build command**: `pip install -r requirements.txt`
4. **Start command** (migrations then API; `PORT` is provided by Render):  
   `bash -c "set -euo pipefail; alembic upgrade head; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"`
5. Confirm environment variables on that same service, for example:
   - `DATABASE_URL` (your production Postgres connection string)
   - `SECRET_KEY`
   - `DEBUG=false`
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS` (your Vercel URL, comma-separated)

---

## 🎨 Frontend Deployment (Vercel)

### Option 1: Using Vercel CLI

```bash
cd backend/frontend
npm i -g vercel
vercel
```

### Option 2: GitHub Integration

1. Push frontend code to GitHub
2. Import project in Vercel dashboard
3. Framework preset: Vite
4. Set environment variable:
   - `VITE_API_URL` = your Render backend URL + `/api/v1`

### After Frontend Deployment

Update backend `ALLOWED_ORIGINS` with your Vercel URL:
```
https://your-app.vercel.app
```

---

## ⚙️ Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://...

# JWT
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App Settings
DEBUG=false
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

### Frontend (.env.production)
```bash
VITE_API_URL=https://your-backend.onrender.com/api/v1
```

---

## 🔒 Security Checklist

- [ ] Strong SECRET_KEY in production
- [ ] DEBUG set to false
- [ ] CORS origins restricted to production domains
- [ ] HTTPS enabled for all services
- [ ] Database credentials secured
- [ ] No console.log in production builds

---

## 📊 Post-Deployment Verification

1. **Health Check**: Visit `https://your-backend.onrender.com/api/v1/health`
   - Should return: `{"status": "ok", "environment": "production"}`

2. **API Docs** (development only): Visit `/docs` endpoint

3. **Frontend**: Test login flow and all CRUD operations

---

## 🛠️ Troubleshooting

### CORS Errors
- Verify `ALLOWED_ORIGINS` includes exact frontend URL
- Check for trailing slashes

### Database Connection
- Verify `DATABASE_URL` format
- Ensure SSL mode is enabled for Supabase

### 401/403 Errors
- Check token expiration settings
- Verify JWT secret consistency

---

## 📝 Useful Commands

```bash
# Backend local (production mode)
cd backend
DEBUG=false uvicorn app.main:app --reload

# Frontend build test
cd backend/frontend
npm run build
npm run preview
```
