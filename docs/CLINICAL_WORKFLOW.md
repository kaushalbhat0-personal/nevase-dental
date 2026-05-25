# Clinical Workflow

> **Last updated:** May 13, 2026
> **Canonical source:** `backend/app/services/encounter_service.py`, `backend/app/services/appointment_service.py`, `backend/app/services/queue_service.py`

---

## 1. Encounter Lifecycle

The appointment is the encounter anchor. There is no separate Visit or Encounter table.

```
Appointment (scheduled)
  → Check-in (front desk)
  → Queue (waiting → in_consultation)
  → Vitals (recorded by nurse/doctor)
  → Consultation (doctor)
  → Prescription (doctor)
  → Inventory consumption (doctor/nurse)
  → Billing (auto-generated or manual)
  → Completion (doctor)
```

---

## 2. Appointment States

Defined in `backend/app/models/appointment.py` (`AppointmentStatus` enum):

| State | Description | Transitions To |
|-------|-------------|----------------|
| `scheduled` | Appointment created, not yet started | `checked_in`, `cancelled` |
| `checked_in` | Patient arrived at clinic | `in_consultation`, `cancelled` |
| `in_consultation` | Patient with doctor | `completed`, `cancelled` |
| `completed` | Encounter finished | (terminal) |
| `cancelled` | Appointment cancelled | (terminal) |

### State Machine Rules

- **Forward-only transitions:** No going back to a previous state
- **Terminal states:** `completed` and `cancelled` cannot transition further
- **Invariant enforcement:** All mutations validate doctor/tenant alignment before state changes

---

## 3. Queue Management

### Queue Entry States

Defined in `backend/app/models/clinic_queue.py` (`QueueStatus` enum):

| State | Description |
|-------|-------------|
| `waiting` | Patient checked in, waiting for doctor |
| `in_consultation` | Patient currently with doctor |
| `completed` | Consultation finished |
| `cancelled` | Patient left without consultation |

### Queue Operations

| Action | Endpoint | Service |
|--------|----------|---------|
| Check-in | `POST /api/v1/clinic-queue/check-in` | `front_desk_service.py` |
| Move to consultation | `PUT /api/v1/clinic-queue/{id}/start-consultation` | `queue_service.py` |
| Complete | `PUT /api/v1/clinic-queue/{id}/complete` | `queue_service.py` |
| Cancel | `PUT /api/v1/clinic-queue/{id}/cancel` | `queue_service.py` |
| List queue | `GET /api/v1/clinic-queue` | `queue_service.py` |

### Front Desk Workflow

1. Patient arrives → Front desk checks them in
2. Queue entry created with status `waiting`
3. Doctor sees patient → Queue moves to `in_consultation`
4. Encounter proceeds → Queue moves to `completed`

---

## 4. Encounter Workspace

### Access

```python
# GET /api/v1/encounters/{appointment_id}
# Requires: has_clinician_capability(db, current_user)
# Returns: EncounterDetailAggregate
```

### EncounterDetailAggregate

The encounter aggregate includes:

| Component | Source | Description |
|-----------|--------|-------------|
| Appointment | `appointment` model | Core appointment data |
| Patient | `patient` model | Patient demographics |
| Doctor | `doctor` model | Doctor profile |
| Vitals | `appointment_vitals` | BP, pulse, temperature, SpO2 |
| Clinical Notes | `appointment.clinical_notes` | Doctor's notes |
| Diagnosis | `appointment.diagnosis` | Primary diagnosis |
| Treatment Summary | `appointment.treatment_summary` | Treatment provided |
| Bills | `bill` model | Associated bills |
| Inventory Items | `appointment_inventory_usage` | Items consumed |
| Queue Entry | `clinic_queue` | Queue status |

### Encounter Completion

```python
# POST /api/v1/appointments/{id}/mark-completed
# Requires: doctor assigned to appointment
# Idempotency-Key header supported
```

**Side effects on completion:**
1. Update appointment status → `completed`
2. Deduct inventory (if `data.items` provided)
3. Generate bill (if `data.generate_bill=True`)
4. Create idempotency record
5. Finalize with `AppointmentInvariantGuard.finalize()`

---

## 5. Vitals Recording

### Supported Vitals

| Vital | Field | Unit |
|-------|-------|------|
| Blood Pressure | `blood_pressure_systolic`, `blood_pressure_diastolic` | mmHg |
| Pulse | `pulse` | bpm |
| Temperature | `temperature` | °C |
| SpO2 | `spo2` | % |
| Respiratory Rate | `respiratory_rate` | breaths/min |
| Weight | `weight` | kg |
| Height | `height` | cm |
| Notes | `notes` | text |

### Vitals Storage

Vitals are stored in `AppointmentVitals` model (linked to appointment):
- One vitals record per appointment
- Recorded during consultation (doctor or nurse)
- Displayed in encounter workspace and patient timeline

---

## 6. Prescription Workflow

### Medication Schedule

Defined in `backend/app/models/patient_medication_schedule.py`:

| Field | Description |
|-------|-------------|
| `patient_id` | Patient (FK) |
| `medication_name` | Drug name |
| `dosage` | Dosage amount |
| `frequency` | How often to take |
| `route` | Administration route (oral, IV, topical, etc.) |
| `duration_days` | Course duration |
| `prescribed_by` | Doctor (FK) |
| `appointment_id` | Associated appointment (optional) |
| `start_date` | When to start |
| `end_date` | When to end |
| `notes` | Additional instructions |
| `is_active` | Whether schedule is active |

### Prescription Flow

1. Doctor prescribes during consultation
2. Medication schedule created via `POST /api/v1/medication-schedules`
3. Patient views schedules in patient workspace
4. Reminders sent based on communication preferences

---

## 7. Inventory Consumption

### Clinical Inventory Usage

```python
# POST /api/v1/appointments/{id}/consume-inventory
# Requires: has_clinician_capability(db, current_user)
```

**Rules:**
- Inventory items must belong to the same tenant as the appointment
- Consumption is tracked in `AppointmentInventoryUsage`
- Stock levels are decremented atomically
- Cannot consume more than available stock

### Inventory Types

| Type | Description |
|------|-------------|
| Consumable | Single-use items (syringes, gloves, bandages) |
| Medication | Drugs administered during visit |
| Equipment | Reusable equipment usage |

---

## 8. Billing During Encounter

### Auto-Generation

When `data.generate_bill=True` is passed during appointment completion:

```python
bill = billing_service.create_bill(
    db=db,
    appointment_id=appointment.id,
    tenant_id=appointment.tenant_id,
    amount=calculated_amount,
    status="pending"
)
```

### Manual Billing

Bills can also be created independently:
- `POST /api/v1/bills` — Create bill (optional `appointment_id`)
- `POST /api/v1/bills/{id}/pay` — Mark bill as paid

### Billing Invariants

- `bill.tenant_id` must match `appointment.tenant_id`
- `bill.appointment_id` must reference a valid appointment (optional)
- Bill status transitions: `pending` → `paid` (no reverse)

---

## 9. Nurse Workflow (Planned)

### Future Nurse Capabilities

| Action | Status | Description |
|--------|--------|-------------|
| Record vitals | Planned | Pre-consultation vitals |
| Prepare patient | Planned | Room assignment, prep |
| Assist doctor | Planned | During consultation |
| Administer medications | Planned | Under doctor orders |
| Discharge instructions | Planned | Post-consultation |

### Nurse Authorization

Nurses will use capability-based authorization similar to doctors:
- `has_nurse_capability(db, current_user)` — checks Nurse record linkage
- Workspace-independent clinical actions

---

## 10. Operational Workflow

### Clinic Operations

Defined in `backend/app/services/clinic_operations_service.py`:

| Feature | Description |
|---------|-------------|
| Operational alerts | Informational notifications (critical, warning, info) |
| Staff tasks | Assignment records (pending → in_progress → completed) |
| Activity feed | Timeline of clinic operations |
| Doctor operations view | Doctor-specific operational dashboard |

### Operational Invariants

- Alerts are informational, not transactional — they do not block operations
- Tasks are not workflow blockers
- All operational data is tenant-scoped

---

## 11. Patient-Facing Workflow

### Patient Workspace

| Feature | Description |
|---------|-------------|
| Appointment list | View upcoming and past appointments |
| Encounter detail | View completed encounter details |
| Health timeline | Chronological view of encounters, vitals, medications |
| Medication schedules | View active and past medications |
| Communication preferences | Notification settings |
| Trusted contacts | Emergency contacts and caregiver access |
| Documents | Uploaded medical documents |
| Care continuity | Summary of ongoing care |

### Patient Access Rules

- Patients can only view their own data
- Patient access is verified via `patient_has_active_appointment_in_tenant()`
- Clinical notes, diagnosis, and treatment_summary are NOT exposed to patient-facing endpoints
- Patient-accessible data: appointments (own), billing (own), medication schedules (own), communication preferences (own)

---

## 12. Encounter Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ENCOUNTER LIFECYCLE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐          │
│  │SCHEDULED │───▶│CHECKED_IN│───▶│IN_CONSULTATION│          │
│  └──────────┘    └──────────┘    └──────┬───────┘          │
│       │                                  │                  │
│       │                                  ├──▶ Vitals        │
│       │                                  ├──▶ Consultation  │
│       │                                  ├──▶ Prescription  │
│       │                                  ├──▶ Inventory     │
│       │                                  │                  │
│       ▼                                  ▼                  │
│  ┌──────────┐                    ┌──────────────┐          │
│  │CANCELLED │                    │  COMPLETED   │          │
│  └──────────┘                    └──────┬───────┘          │
│                                         │                  │
│                                         ├──▶ Bill          │
│                                         ├──▶ Idempotency   │
│                                         └──▶ Audit Log     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
