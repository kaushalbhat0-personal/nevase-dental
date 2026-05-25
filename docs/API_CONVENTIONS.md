# API Conventions

> **Last updated:** May 13, 2026
> **Canonical source:** `backend/app/api/v1/`

---

## 1. Base URL

All endpoints are under `/api/v1/`.

| Environment | URL |
|-------------|-----|
| Local development | `http://localhost:8000/api/v1` |
| Production | `https://your-api.onrender.com/api/v1` |

---

## 2. Authentication

### JWT Bearer Token

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

### Token Acquisition

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/register` | POST | Create user + return token |
| `/api/v1/login` | POST | Authenticate + return token |
| `/api/v1/me` | GET | Current user details (protected) |

### Token Claims

```json
{
  "sub": "user-uuid",
  "role": "doctor",
  "roles": ["doctor"],
  "tenant_id": "tenant-uuid",
  "exp": 1234567890
}
```

---

## 3. Request/Response Conventions

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes (protected routes) | `Bearer <token>` |
| `Content-Type` | Yes (POST/PUT) | `application/json` |
| `Idempotency-Key` | No (CREATE operations) | UUID for idempotent retries |
| `X-Tenant-ID` | No | Tenant context override (validated) |
| `X-Workspace` | No | Workspace context (UI-oriented) |

### Response Format

**Success:**
```json
{
  "id": "uuid",
  "field1": "value1",
  "field2": "value2"
}
```

**List responses:**
```json
[
  { "id": "uuid1", ... },
  { "id": "uuid2", ... }
]
```

**Error responses:**
```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Status | Usage |
|--------|-------|
| 200 OK | Successful GET/PUT/PATCH |
| 201 Created | Successful POST |
| 204 No Content | Successful DELETE |
| 400 Bad Request | Validation errors |
| 401 Unauthorized | Missing/invalid authentication |
| 403 Forbidden | Insufficient permissions |
| 404 Not Found | Missing resources |
| 409 Conflict | Idempotency key conflicts |
| 422 Unprocessable Entity | Pydantic validation errors |
| 500 Internal Server Error | Unexpected errors |

---

## 4. Idempotency Pattern

### Supported Operations

| Operation | Idempotency Table |
|-----------|-------------------|
| Create tenant | `tenant_creation_idempotency` |
| Create appointment | `appointment_creation_idempotency` |
| Create doctor | `doctor_creation_idempotency` |
| Complete appointment | `appointment_completion_idempotency` |

### How It Works

1. Client sends `Idempotency-Key: <uuid>` header
2. Server hashes the request body
3. Checks idempotency table for existing key:
   - **Same key + same hash** → Return cached result (idempotent replay)
   - **Same key + different hash** → `409 Conflict`
   - **New key** → Execute operation, store key+hash+result
4. Returns `201 Created` (or appropriate status)

### Client Usage

```javascript
// Frontend example
const response = await axios.post(
  '/api/v1/appointments',
  { patient_id, doctor_id, appointment_time },
  {
    headers: {
      'Idempotency-Key': crypto.randomUUID(),
    },
  }
);
```

---

## 5. Tenant Scoping

### Automatic Scoping

Most endpoints automatically scope queries to the current tenant:

```python
# Dependency resolves tenant from JWT or X-Tenant-ID header
tenant_id = get_scoped_tenant_id(db, current_user, x_tenant_id)
```

### Super Admin Override

Super admin can pass `?tenant_id=` query parameter for cross-tenant operations:

```
GET /api/v1/doctors?tenant_id=<target-tenant-uuid>
```

### Tenant-Aware Endpoints

| Endpoint | Tenant Behavior |
|----------|-----------------|
| `GET /api/v1/patients` | Scoped to tenant (patients with appointments in tenant) |
| `GET /api/v1/doctors` | Scoped to tenant |
| `GET /api/v1/appointments` | Scoped to tenant |
| `GET /api/v1/bills` | Scoped to tenant |
| `POST /api/v1/doctors` | Tenant from context (super admin can override) |

---

## 6. Endpoint Index

### Patients

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/patients` | List patients (search by name) |
| POST | `/api/v1/patients` | Create patient |
| GET | `/api/v1/patients/{id}` | Get patient detail |
| PUT | `/api/v1/patients/{id}` | Update patient (including clinical_notes) |

### Doctors

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/doctors` | List doctors (tenant-aware) |
| POST | `/api/v1/doctors` | Create doctor (admin/super_admin, idempotent) |
| GET | `/api/v1/doctors/{id}` | Get doctor detail |
| GET | `/api/v1/doctors/{id}/availability` | Get availability windows |
| GET | `/api/v1/doctors/{id}/bookable-slots` | Get bookable slots |

### Appointments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/appointments` | List appointments (with filters) |
| POST | `/api/v1/appointments` | Create appointment (idempotent) |
| PUT | `/api/v1/appointments/{id}` | Update appointment |
| POST | `/api/v1/appointments/{id}/mark-completed` | Complete appointment (idempotent) |
| POST | `/api/v1/appointments/{id}/consume-inventory` | Consume clinical inventory |

### Billing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/bills` | List bills |
| POST | `/api/v1/bills` | Create bill |
| POST | `/api/v1/bills/{id}/pay` | Mark bill as paid |

### Encounters

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/encounters/{appointment_id}` | Get encounter aggregate |
| PUT | `/api/v1/encounters/{appointment_id}/vitals` | Update vitals |

### Queue

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/clinic-queue` | List queue entries |
| POST | `/api/v1/clinic-queue/check-in` | Check in patient |
| PUT | `/api/v1/clinic-queue/{id}/start-consultation` | Start consultation |
| PUT | `/api/v1/clinic-queue/{id}/complete` | Complete queue entry |
| PUT | `/api/v1/clinic-queue/{id}/cancel` | Cancel queue entry |

### Front Desk

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/front-desk/dashboard` | Front desk dashboard data |

### Nurse Workflow

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/nurse-workflow/queue` | Nurse queue view |
| PUT | `/api/v1/nurse-workflow/{id}/record-vitals` | Record vitals |

### Clinic Operations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/clinic-operations/dashboard` | Operations dashboard |
| GET | `/api/v1/clinic-operations/alerts` | Operational alerts |
| GET | `/api/v1/clinic-operations/tasks` | Staff tasks |
| POST | `/api/v1/clinic-operations/tasks` | Create task |
| PUT | `/api/v1/clinic-operations/tasks/{id}` | Update task |

### Medication Schedules

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/medication-schedules` | List schedules |
| POST | `/api/v1/medication-schedules` | Create schedule |
| PUT | `/api/v1/medication-schedules/{id}` | Update schedule |
| DELETE | `/api/v1/medication-schedules/{id}` | Delete schedule |

### Notifications & Communications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/communications/preferences` | Get communication preferences |
| PUT | `/api/v1/communications/preferences` | Update preferences |
| POST | `/api/v1/communications/send` | Send notification |

### Patient Workspace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/patient-workspace/dashboard` | Patient dashboard |
| GET | `/api/v1/patient-workspace/appointments` | Patient appointments |
| GET | `/api/v1/patient-workspace/encounters/{id}` | Patient encounter detail |

### Branding

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/branding/profile` | Get tenant branding |
| PUT | `/api/v1/branding/profile` | Update tenant branding |

### Procurement

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/procurement/inventory` | List inventory |
| POST | `/api/v1/procurement/inventory` | Add inventory item |
| GET | `/api/v1/procurement/suppliers` | List suppliers |
| POST | `/api/v1/procurement/suppliers` | Create supplier |
| GET | `/api/v1/procurement/purchase-orders` | List purchase orders |
| POST | `/api/v1/procurement/purchase-orders` | Create purchase order |

### Reporting

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reporting/appointments` | Appointment reports |
| GET | `/api/v1/reporting/revenue` | Revenue reports |
| GET | `/api/v1/reporting/inventory` | Inventory reports |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/integrity-scan` | Run integrity scan |
| GET | `/api/v1/admin/dashboard` | Admin dashboard |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents/{id}` | Get document |
| DELETE | `/api/v1/documents/{id}` | Delete document |

---

## 7. Error Handling

### Service Layer Exceptions

Defined in `backend/app/services/exceptions.py`:

```python
class ServiceError(Exception):      # Base exception
class NotFoundError(ServiceError):   # 404
class ForbiddenError(ServiceError):  # 403
class ConflictError(ServiceError):   # 409
class ValidationError(ServiceError): # 400
```

### Exception Handlers

FastAPI exception handlers in `backend/app/main.py`:

```python
@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

---

## 8. Adding New Endpoints

### Step-by-Step

1. **Create schema** in `backend/app/schemas/` (Pydantic request/response models)
2. **Create CRUD** in `backend/app/crud/` (database operations)
3. **Create service** in `backend/app/services/` (business logic, transactions, idempotency)
4. **Create router** in `backend/app/api/v1/endpoints/` (route handlers)
5. **Register router** in `backend/app/api/v1/router.py`
6. **Write tests** in `backend/tests/`

### Required Patterns

```python
# Router pattern
router = APIRouter(prefix="/resource", tags=["Resource"])

@router.get("/", response_model=list[ResourceOut])
async def list_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
):
    return resource_service.list_resources(db, tenant_id=tenant_id)

@router.post("/", response_model=ResourceOut, status_code=201)
async def create_resource(
    data: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_scoped_tenant_id),
    idempotency_key: str | None = Header(None),
):
    return resource_service.create_resource(
        db, data=data, tenant_id=tenant_id,
        created_by=current_user.id, idempotency_key=idempotency_key,
    )
```
