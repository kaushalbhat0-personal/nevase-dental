# Hospital Management System (Medical Webapp)

Full-stack Hospital Management System with comprehensive clinical workflow support:

## System Overview

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- **Frontend**: React + TypeScript + Vite (in `backend/frontend`)
- **Architecture**: Multi-tenant SaaS architecture with role-based access control
- **Key Features**: Appointment management, electronic prescriptions, billing, inventory management, clinical documentation

## Core Capabilities

### Clinical Workflow
- **Appointment Lifecycle**: Scheduling, check-in, vitals recording, prescription generation, completion
- **Electronic Prescriptions**: Medication prescribing with auto-derivation of patient medication schedules
- **Clinical Documentation**: SOAP notes support (subjective, objective, assessment, plan)
- **Vital Signs Tracking**: Comprehensive vital signs recording during encounters

### Prescription System (Enhanced)
- **Prescription Creation**: Structured prescription creation with medicine items
- **Automated Scheduling**: Automatic derivation of PatientMedicationSchedule records from prescriptions
- **Duration Parsing**: Support for parsing duration strings (e.g., "7 days", "2 weeks", "1 month")
- **Audit Trail**: Complete audit logging for prescription creation and updates
- **Idempotency Protection**: Idempotency key support for safe prescription operations

### Security & Compliance
- **JWT Authentication**: Role-based access control with fine-grained permissions
- **Multi-tenancy**: Tenant isolation for SaaS deployment
- **CORS Protection**: Explicit origin validation (no wildcards in production)
- **Rate Limiting**: Abuse prevention for public and authenticated endpoints
- **Audit Logging**: Structured audit trails for all clinical and administrative actions

### Technical Features
- **Idempotency Keys**: Safe retry mechanisms for critical operations
- **Request Tracing**: X-Request-ID headers for distributed tracing
- **Health Checks**: Liveness and readiness probes for container orchestration
- **Database Migrations**: Alembic-based schema evolution
- **Structured Logging**: JSON-compatible logs for observability platforms

## Requirements

- Python 3.10+
- Node.js (for the frontend)
- PostgreSQL (local or hosted, e.g. Supabase)

## Technology Stack

### Backend
- **Framework**: FastAPI (modern, high-performance Python web framework)
- **ORM**: SQLAlchemy 2.0 (with async support)
- **Database**: PostgreSQL (relational database)
- **Migrations**: Alembic (database schema versioning)
- **Validation**: Pydantic (data validation and settings management)
- **Authentication**: JWT (JSON Web Tokens) for secure API access
- **Testing**: pytest (testing framework)

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite (fast development server and bundler)
- **State Management**: React Context API and hooks
- **HTTP Client**: Axios for API communication
- **UI Components**: Custom component library with responsive design

### Infrastructure
- **Containerization**: Docker support for consistent deployment
- **Observability**: Structured logging, request tracing, health check endpoints
- **Security**: CORS protection, rate limiting, input validation

## Quick start (local development)

### 1) Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` (start from `backend/.env.example`) and set at minimum:

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

Run the API (from `backend`, venv activated):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Health**: `GET /health` (no API prefix)
- **API base path**: `/api/v1`
- **API health**: `GET /api/v1/health`
- **Docs**: `http://127.0.0.1:8000/docs`

### 2) Frontend setup

```bash
cd backend/frontend
npm install
```

Create `backend/frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

Run the frontend:

```bash
npm run dev
```

Open `http://localhost:5173`.

## API Endpoints Overview

### Authentication
- `POST /api/v1/register` - Create user account
- `POST /api/v1/login` - Authenticate user
- `GET /api/v1/me` - Get current user info (protected)

### Appointments
- `GET /api/v1/appointments` - List appointments (with filtering)
- `POST /api/v1/appointments` - Create appointment
- `GET /api/v1/appointments/{id}` - Get appointment details
- `PUT /api/v1/appointments/{id}` - Update appointment
- `DELETE /api/v1/appointments/{id}` - Cancel appointment
- `POST /api/v1/appointments/{id}/complete` - Mark appointment as completed

### Prescriptions
- `POST /api/v1/appointments/{id}/prescriptions` - Create prescription for appointment
- `GET /api/v1/appointments/{id}/prescriptions` - Get prescriptions for appointment
- `PUT /api/v1/prescriptions/{id}` - Update prescription
- `GET /api/v1/prescriptions/{id}` - Get prescription details

### Patients
- `GET /api/v1/patients` - List patients
- `POST /api/v1/patients` - Create patient record
- `GET /api/v1/patients/{id}` - Get patient details

### Doctors
- `GET /api/v1/doctors` - List doctors
- `POST /api/v1/doctors` - Create doctor profile
- `GET /api/v1/doctors/{id}` - Get doctor details

### Inventory
- `GET /api/v1/inventory` - List inventory items
- `POST /api/v1/inventory` - Add inventory item
- `PUT /api/v1/inventory/{id}` - Update inventory item

### Billing
- `GET /api/v1/billing` - List bills
- `POST /api/v1/billing` - Generate bill
- `GET /api/v1/billing/{id}` - Get bill details

## Authentication (JWT)

The API uses JWT Bearer tokens for protected routes.

- `POST /api/v1/register` creates a user and returns `access_token`
- `POST /api/v1/login` returns `access_token` for existing credentials
- `GET /api/v1/me` returns current user details (protected)

Authorization header:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

## Authentication (JWT)

The API uses JWT Bearer tokens for protected routes.

- `POST /api/v1/register` creates a user and returns `access_token`
- `POST /api/v1/login` returns `access_token` for existing credentials
- `GET /api/v1/me` returns current user details (protected)

Authorization header:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

## Documentation

All documentation is in the `docs/` directory:

| Document | Description |
|----------|-------------|
| `docs/PROJECT_OVERVIEW.md` | High-level project overview and tech stack |
| `docs/ARCHITECTURE.md` | System architecture, patterns, and layering |
| `docs/AUTHORIZATION_MODEL.md` | Identity, capability, and workspace authorization |
| `docs/MULTI_TENANCY.md` | Multi-tenant architecture and tenant isolation |
| `docs/CLINICAL_WORKFLOW.md` | Encounter lifecycle, queue, vitals, prescriptions |
| `docs/API_CONVENTIONS.md` | API patterns, idempotency, endpoint index |
| `docs/FRONTEND_STRUCTURE.md` | Frontend workspace architecture and components |
| `docs/MIGRATION_GUIDE.md` | Alembic migration governance and safety |
| `docs/DEPLOYMENT.md` | Deployment guide (Render + Vercel) |
| `docs/ROADMAP.md` | Implemented features, in-progress, and planned work |

### Additional References

- **Production fixes**: see `PRODUCTION_FIXES.md`
- **Migration audit**: see `backend/MIGRATION_AUDIT_REPORT.md`
- **Migration cleanup strategy**: see `backend/MIGRATION_CLEANUP_STRATEGY.md`
- **Project summary**: see `PROJECT_SUMMARY.md`
- **Deployment**: see `DEPLOYMENT.md` (root) or `docs/DEPLOYMENT.md`
- **Trace prescriptions analysis**: see `_trace_prescriptions.py` (diagnostic tool for prescription flow)

## Prescription System Details

The prescription system includes:

### Prescription Creation
- Prescriptions are created during appointment completion via the `mark_appointment_completed` endpoint
- Each prescription can contain multiple medicine items with dosage, frequency, duration, and instructions
- System supports free-text notes for additional prescription information

### Automated Medication Scheduling
- When a prescription is created, the system automatically derives `PatientMedicationSchedule` records
- These schedules represent the canonical patient medication plan, independent of inventory or billing
- Duration strings are parsed to calculate end dates (supports formats like "7 days", "2 weeks", "1 month")

### Prescription Management
- Prescriptions can be created standalone or in conjunction with appointment completion
- Prescription updates maintain audit trails
- Full prescription history is maintained per appointment

### Security Features
- Prescription operations require appropriate clinical capabilities
- Tenant isolation ensures prescriptions are only accessible within the appropriate tenant
- Idempotency keys prevent duplicate prescription creation
- Comprehensive audit logging tracks all prescription creation and modifications

## Project layout

| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI application entry |
| `backend/app/core/` | Settings and database session |
| `backend/app/models/` | SQLAlchemy models |
| `backend/app/schemas/` | Pydantic schemas |
| `backend/app/api/v1/` | API routers and endpoints |
| `backend/alembic/` | Migration environment and scripts |
| `backend/frontend/` | React + Vite frontend |
