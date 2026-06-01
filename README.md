# Nevase Dental Clinic

Dental practice management system for Nevase Dental Clinic. Manages patients, appointments, billing, inventory, and clinical documentation in a single-clinic setup.

## System Overview

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- **Frontend**: React + TypeScript + Vite (in `frontend/`)
- **Architecture**: Single-tenant clinic management with role-based access (admin, doctor)
- **Key Features**: Appointment scheduling, patient records, electronic prescriptions, billing, inventory management, clinical encounter documentation

## Core Capabilities

### Clinical Workflow
- **Appointment Lifecycle**: Scheduling, check-in, vitals recording, prescription generation, completion
- **Electronic Prescriptions**: Medication prescribing with auto-derivation of patient medication schedules
- **Clinical Documentation**: SOAP notes (subjective, objective, assessment, plan)
- **Vital Signs Tracking**: Recording during encounters

### Practice Management
- **Patient Management**: Registration, history, documents, family linking
- **Doctor Availability**: Weekly schedule windows with slot-based booking
- **Billing**: Invoice generation, payment tracking per patient
- **Inventory**: Clinic consumables and supplies tracking

### Security
- **JWT Authentication**: Role-based access (admin, doctor)
- **CORS Protection**: Explicit origin validation
- **Audit Logging**: Structured audit trails for clinical and administrative actions

## Quick Start

### 1) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
SECRET_KEY=change-me
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Apply migrations:

```bash
cd backend
alembic upgrade head
```

Run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API docs**: `http://127.0.0.1:8000/docs`

### 2) Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

Run:

```bash
npm run dev
```

Open `http://localhost:5173`.

## Default Admin Login

After seeding, log in with:

- Email: `admin@nevase.com`
- Password: `Admin@123`

## Project Layout

| Path | Purpose |
|------|---------|
| `backend/app/` | FastAPI application code |
| `backend/app/core/` | Settings, database, security |
| `backend/app/models/` | SQLAlchemy ORM models |
| `backend/app/schemas/` | Pydantic request/response schemas |
| `backend/app/api/v1/` | API routers and endpoints |
| `backend/app/services/` | Business logic layer |
| `backend/alembic/` | Database migrations |
| `frontend/src/` | React application code |
| `frontend/src/pages/` | Page components |
| `frontend/src/components/` | Shared UI components |
| `app/` | Additional services |
