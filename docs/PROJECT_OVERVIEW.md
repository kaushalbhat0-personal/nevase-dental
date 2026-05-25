# Project Overview

> **Last updated:** May 13, 2026
> **Status:** Active development — multi-tenant healthcare platform

---

## 1. What Is This?

A production-oriented **multi-tenant hospital management system** (Hospital ERP) built for independent doctors, tenant-based clinics, and healthcare organizations. The system manages the full patient care lifecycle — from appointment scheduling through clinical encounters, billing, and follow-up.

### Core Capabilities

- **Multi-tenant architecture** — Each clinic/doctor practice is a tenant with isolated data
- **Role-aware workspaces** — Frontend adapts to user role (admin, doctor, patient, front desk, operations, procurement, finance)
- **Clinical encounter workflows** — Check-in → Queue → Vitals → Consultation → Prescription → Inventory → Billing → Completion
- **Capability-based authorization** — Clinical actions are authorized by Doctor record linkage, not role names
- **Patient portal** — Patients can view timeline, medications, communications, documents, and more
- **Inventory & procurement** — Track supplies, manage purchase orders, consume inventory during encounters
- **Reporting & analytics** — Appointment, revenue, and inventory reports with export

---

## 2. Tech Stack

### Backend

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI (Python 3.11+) |
| **ORM** | SQLAlchemy 2.0 (Mapped style) |
| **Migrations** | Alembic |
| **Database** | PostgreSQL (primary), SQLite (test) |
| **Auth** | JWT Bearer tokens |
| **Validation** | Pydantic v2 |
| **Testing** | pytest, pytest-asyncio, httpx |

### Frontend

| Component | Technology |
|-----------|-----------|
| **Framework** | React 19 |
| **Language** | TypeScript 6 |
| **Build Tool** | Vite 8 |
| **Styling** | Tailwind CSS 3 |
| **Routing** | React Router DOM v7 |
| **HTTP Client** | Axios |
| **UI Library** | shadcn/ui |
| **Icons** | Lucide React |
| **Validation** | Zod |
| **Testing** | Playwright (E2E) |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| **Backend Hosting** | Render |
| **Frontend Hosting** | Vercel |
| **Database** | Supabase (PostgreSQL) |
| **Caching** | Redis / Upstash (where configured) |

---

## 3. Repository Structure

```
medical_webapp/
├── .clinerules                    # AI development rules
├── .cursor/rules/                 # Cursor-specific rules
├── docs/                          # Documentation (this directory)
├── DEPLOYMENT.md                  # Deployment guide (root)
├── PRODUCTION_FIXES.md            # Production issue tracking
├── PROJECT_SUMMARY.md             # Detailed project summary
├── README.md                      # Quick start guide
├── task_progress.md               # Task tracking
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── core/                  # Settings, database, auth, tenancy
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── crud/                  # Database operations
│   │   ├── services/              # Business logic layer
│   │   └── api/v1/                # API routers and endpoints
│   ├── alembic/                   # Migration scripts
│   ├── tests/                     # Backend test suite
│   ├── scripts/                   # Utility scripts
│   └── frontend/                  # React frontend (embedded)
│       └── src/
│           ├── workspace/         # Workspace system
│           ├── pages/             # Page components
│           ├── components/        # UI components
│           ├── services/          # API client functions
│           ├── hooks/             # Custom React hooks
│           ├── types/             # TypeScript interfaces
│           └── utils/             # Helper functions
│
└── package.json                   # Root package.json
```

---

## 4. Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Appointment as encounter anchor** | No separate Visit table; appointment is the single source of truth for encounters |
| **Global patient architecture** | `patient.tenant_id` is always NULL; tenant context derived from appointments |
| **Capability-based clinical auth** | Clinical actions authorized by Doctor record linkage, not role names |
| **Workspace-independent permissions** | Workspace is UI context only; does not determine clinical permission |
| **Resource ownership is authoritative** | Frontend tenant IDs and JWT claims are hints; resource tenant_id is truth |
| **Idempotency for all CREATE operations** | Safe retries via `Idempotency-Key` header |
| **Additive migrations only** | Never drop columns or tables; backward-compatible changes only |

---

## 5. User Roles

| Role | Description |
|------|-------------|
| `super_admin` | Cross-tenant system administrator |
| `admin` | Tenant-level administrator |
| `doctor` | Clinician with patient care capabilities |
| `staff` | Tenant staff (receptionist, nurse, etc.) |
| `patient` | End-user accessing patient portal |

---

## 6. Workspaces

| Workspace | Slug | Primary Users |
|-----------|------|---------------|
| Admin | `admin` | super_admin, admin |
| Doctor | `doctor` | doctor |
| Patient | `patient` | patient |
| Front Desk | `front-desk` | staff (receptionist) |
| Operations | `operations` | staff (operations) |
| Procurement | `procurement` | staff (procurement) |
| Finance | `finance` | staff (finance) |

---

## 7. Current Status

The system is in **active development** (v0.7). Core clinical workflows are implemented. Patient portal, queue management, procurement, and reporting are functional. See `docs/ROADMAP.md` for detailed status.

### Implemented Highlights

- ✅ Multi-tenant architecture with tenant isolation
- ✅ JWT authentication with role-based access
- ✅ Capability-based clinical authorization
- ✅ Appointment lifecycle (scheduling → completion)
- ✅ Encounter workspace (vitals, notes, diagnosis, treatment)
- ✅ Inventory consumption during encounters
- ✅ Billing (create, pay, tenant-scoped)
- ✅ Queue management (check-in, consultation, completion)
- ✅ Patient portal (timeline, medications, communications, documents)
- ✅ Clinic operations (alerts, tasks, activity feed)
- ✅ Procurement (inventory, suppliers, purchase orders)
- ✅ Reporting (appointments, revenue, inventory)
- ✅ Tenant branding and organization profiles
- ✅ Notifications and communication preferences
- ✅ Integrity scanning and audit logging
- ✅ 6 workspace layouts with route isolation
- ✅ 49 migration files with single healthy head

---

## 8. Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

### Quick Start

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd backend/frontend
npm install
npm run dev
```

See `README.md` for detailed setup instructions.

---

## 9. Documentation Index

| Document | Description |
|----------|-------------|
| `docs/ARCHITECTURE.md` | System architecture, patterns, and layering |
| `docs/AUTHORIZATION_MODEL.md` | Identity, capability, and workspace authorization |
| `docs/MULTI_TENANCY.md` | Multi-tenant architecture and tenant isolation |
| `docs/CLINICAL_WORKFLOW.md` | Encounter lifecycle, queue, vitals, prescriptions |
| `docs/API_CONVENTIONS.md` | API patterns, idempotency, endpoint index |
| `docs/FRONTEND_STRUCTURE.md` | Frontend workspace architecture and components |
| `docs/MIGRATION_GUIDE.md` | Alembic migration governance and safety |
| `docs/DEPLOYMENT.md` | Deployment guide (Render + Vercel) |
| `docs/ROADMAP.md` | Implemented features, in-progress, and planned work |
