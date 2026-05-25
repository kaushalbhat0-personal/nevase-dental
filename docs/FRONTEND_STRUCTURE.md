# Frontend Structure

> **Location:** `backend/frontend/`

---

## 1. Overview

The frontend is a React 19 + TypeScript application built with Vite, embedded inside the backend directory.

| Aspect | Detail |
|--------|--------|
| **Framework** | React 19 |
| **Language** | TypeScript 6 |
| **Build Tool** | Vite 8 |
| **Styling** | Tailwind CSS 3 + Custom CSS |
| **Routing** | React Router DOM v7 |
| **HTTP Client** | Axios |
| **Icons** | Lucide React |
| **Toast** | React Hot Toast |
| **Animations** | Framer Motion |
| **UI Library** | shadcn/ui (components in `components/ui/`) |
| **Form Validation** | Zod (schemas in `validation/`) |

---

## 2. Directory Structure

```
backend/frontend/src/
├── App.tsx                    # Main app with routing
├── main.tsx                   # React entry point
├── index.css                  # Global styles + Tailwind
├── vite-env.d.ts              # Vite type declarations
│
├── workspace/                 # Workspace system (DO NOT REWRITE)
│   ├── registry.tsx           # Workspace definitions (SINGLE SOURCE OF TRUTH)
│   ├── resolver.ts            # Workspace resolution from user context
│   ├── route-isolation.tsx    # Route scoping by workspace
│   ├── WorkspaceSwitcher.tsx  # Workspace switching UI
│   ├── contextual-redirects.ts # Post-login redirect logic
│   ├── useActiveWorkspace.ts  # Active workspace hook
│   ├── index.ts               # Barrel exports
│   └── layouts/               # Workspace-specific layouts
│       ├── DoctorWorkspaceLayout.tsx
│       ├── PatientWorkspaceLayout.tsx
│       ├── FrontDeskWorkspaceLayout.tsx
│       ├── OperationsWorkspaceLayout.tsx
│       ├── ProcurementWorkspaceLayout.tsx
│       ├── FinanceWorkspaceLayout.tsx
│       └── contextual-header.tsx
│
├── pages/                     # Page components (data fetching)
│   ├── doctor/
│   │   ├── DoctorAppointmentsPage.tsx
│   │   ├── DoctorAppointmentDetailPage.tsx
│   │   ├── DoctorPatientDetailPage.tsx
│   │   └── EncounterWorkspacePage.tsx
│   ├── patient/
│   │   ├── PatientHome.tsx
│   │   ├── PatientCareHub.tsx
│   │   ├── PatientHealthTimeline.tsx
│   │   ├── PatientEncounterDetail.tsx
│   │   ├── PatientMedicines.tsx
│   │   ├── PatientCommunicationCenter.tsx
│   │   ├── PatientVitalsHistory.tsx
│   │   ├── PatientFamilyHub.tsx
│   │   ├── PatientEmergencyProfile.tsx
│   │   ├── PatientProfile.tsx
│   │   ├── PatientProfileSettings.tsx
│   │   ├── PatientDocuments.tsx
│   │   ├── PatientDiscover.tsx
│   │   ├── PatientFollowUps.tsx
│   │   └── PatientAppointments.tsx
│   ├── procurement/
│   │   ├── PurchaseEntryModal.tsx
│   │   ├── SupplierManagement.tsx
│   │   └── ProcurementReports.tsx
│   ├── AdminBrandingPage.tsx
│   ├── AdminCommunicationsPage.tsx
│   ├── AdminFinancialDashboard.tsx
│   ├── AdminProcurementDashboard.tsx
│   ├── Dashboard.tsx
│   ├── Patients.tsx
│   ├── Doctors.tsx
│   ├── Appointments.tsx
│   ├── Billing.tsx
│   └── Login.tsx
│
├── components/                # Reusable UI components
│   ├── ui/                    # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── select.tsx
│   │   ├── switch.tsx
│   │   ├── checkbox.tsx
│   │   ├── tabs.tsx
│   │   ├── label.tsx
│   │   └── page-section.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── DoctorSidebar.tsx
│   │   ├── PatientLayout.tsx
│   │   ├── PatientBottomNav.tsx
│   │   └── doctorNav.ts
│   ├── doctor/
│   │   └── calendar/
│   │       └── DayCalendar.tsx
│   ├── patient/
│   │   ├── VitalTrendCard.tsx
│   │   ├── CommunicationCard.tsx
│   │   ├── CommunicationPreferences.tsx
│   │   ├── ReminderSection.tsx
│   │   ├── EncounterHeroCard.tsx
│   │   ├── PatientCareContinuityCard.tsx
│   │   ├── EncounterJourneySection.tsx
│   │   ├── TimelineEncounterCard.tsx
│   │   ├── DependentProfileCard.tsx
│   │   ├── CaregiverAccessCard.tsx
│   │   ├── EmergencyInfoCard.tsx
│   │   ├── PatientHealthSummaryCard.tsx
│   │   ├── TrustedContactCard.tsx
│   │   ├── TrustedContactsSection.tsx
│   │   ├── UpcomingVisitChecklist.tsx
│   │   └── VisitPreparationCard.tsx
│   ├── frontdesk/
│   │   ├── FrontDeskDashboard.tsx
│   │   ├── AppointmentStatusActions.tsx
│   │   └── QueueManagementPanel.tsx
│   └── operations/
│       ├── ClinicOperationsDashboard.tsx
│       ├── AlertSeverityChip.tsx
│       ├── ActivityTimelineCard.tsx
│       ├── StaffTaskCard.tsx
│       ├── OperationalTaskList.tsx
│       ├── StaffOperationsSummary.tsx
│       ├── DoctorOperationsView.tsx
│       └── OperationalAlertBanner.tsx
│
├── services/                  # API client functions (axios)
│   ├── api.ts                 # Base axios configuration
│   ├── index.ts               # Barrel exports
│   ├── appointments.ts
│   ├── billing.ts
│   ├── patients.ts
│   ├── doctors.ts
│   ├── clinicQueue.ts
│   ├── clinicOperations.ts
│   ├── branding.ts
│   ├── notifications.ts
│   ├── patientWorkspace.ts
│   ├── patientCommunications.ts
│   ├── medicationSchedule.ts
│   ├── dailyCare.ts
│   ├── procurement.ts
│   ├── reporting.ts
│   ├── documents.ts
│   └── trustAndFamily.ts
│
├── hooks/                     # Custom React hooks
│   ├── useAuth.ts
│   ├── useDashboard.ts
│   ├── usePatients.ts
│   ├── useDoctors.ts
│   ├── useAppointments.ts
│   └── useBilling.ts
│
├── handlers/                  # API call handlers
│   └── billingHandler.ts
│
├── types/                     # TypeScript interfaces
│   └── index.ts
│
├── validation/                # Zod schemas
│   └── schemas.ts
│
├── utils/                     # Helper functions
│   ├── patientTimeline.ts
│   ├── continuity.ts
│   ├── trustSignals.ts
│   ├── familyHelpers.ts
│   └── preparationChecklist.ts
│
├── constants/                 # App constants
│   └── index.ts
│
└── animations/                # Framer Motion components
    └── index.ts
```

---

## 3. Workspace Architecture

### Workspace Registry

`workspace/registry.tsx` is the **single source of truth** for workspace definitions:

```typescript
// Each workspace has:
interface WorkspaceDefinition {
  slug: string;           // URL-safe identifier
  label: string;          // Display name
  icon: LucideIcon;       // Icon component
  roles: string[];        // Allowed roles
  layout: React.ComponentType;  // Layout component
}
```

### Workspace Resolution

`workspace/resolver.ts` determines which workspace a user should see:

1. After login, `resolver.ts` checks user roles
2. Maps roles to allowed workspaces
3. Redirects to the first matching workspace

### Route Isolation

`workspace/route-isolation.tsx` enforces workspace scoping:

- Routes are wrapped in workspace-specific guards
- Users cannot navigate to workspaces they don't have access to
- Workspace context is passed via `X-Workspace` header to API calls

### Workspace Layouts

Each workspace has a dedicated layout in `workspace/layouts/`:

| Layout | Workspace | Features |
|--------|-----------|----------|
| `DoctorWorkspaceLayout` | Doctor | Sidebar with patient list, calendar, encounter access |
| `PatientWorkspaceLayout` | Patient | Bottom nav, health timeline, appointments |
| `FrontDeskWorkspaceLayout` | Front Desk | Queue management, check-in |
| `OperationsWorkspaceLayout` | Operations | Alerts, tasks, activity feed |
| `ProcurementWorkspaceLayout` | Procurement | Inventory, suppliers, purchase orders |
| `FinanceWorkspaceLayout` | Finance | Billing overview, reports |

---

## 4. Route Structure

```
/                           → Workspace resolver (redirects based on role)
/login                      → Login page
/signup                     → Signup page
/reset-password             → Password reset

/admin/*                    → Admin workspace
  /admin                    → Admin dashboard
  /admin/patients           → Patient management
  /admin/doctors            → Doctor management
  /admin/appointments       → Appointment management
  /admin/billing            → Billing overview
  /admin/branding           → Tenant branding
  /admin/communications     → Communication settings
  /admin/procurement        → Procurement dashboard
  /admin/financial          → Financial dashboard

/doctor/*                   → Doctor workspace
  /doctor                   → Doctor dashboard
  /doctor/appointments      → Appointment list
  /doctor/appointments/:id  → Appointment detail
  /doctor/patients/:id      → Patient detail
  /doctor/encounter/:id     → Encounter workspace

/patient/*                  → Patient workspace
  /patient                  → Patient home
  /patient/appointments     → My appointments
  /patient/encounters/:id   → Encounter detail
  /patient/timeline         → Health timeline
  /patient/medicines        → Medication schedules
  /patient/communications   → Communication center
  /patient/vitals           → Vitals history
  /patient/family           → Family hub
  /patient/emergency        → Emergency profile
  /patient/profile          → Profile settings
  /patient/documents        → Medical documents
  /patient/discover         → Discover

/front-desk/*               → Front desk workspace
  /front-desk               → Front desk dashboard

/operations/*               → Operations workspace
  /operations               → Operations dashboard

/procurement/*              → Procurement workspace
  /procurement              → Procurement dashboard
  /procurement/suppliers    → Supplier management
  /procurement/reports      → Procurement reports

/finance/*                  → Finance workspace
  /finance                  → Financial dashboard
```

---

## 5. Services Layer

### Base Configuration

`services/api.ts` configures the Axios instance:

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
});
```

### Interceptors

- **Request interceptor:** Attaches `Authorization: Bearer <token>` header
- **Response interceptor:** Handles 401 (redirect to login), 403 (show toast), 500 (show error)

### Service Pattern

```typescript
// services/appointments.ts
export const appointmentsApi = {
  list: (params?: AppointmentFilters) =>
    api.get<Appointment[]>('/appointments', { params }),

  get: (id: string) =>
    api.get<Appointment>(`/appointments/${id}`),

  create: (data: CreateAppointmentData, idempotencyKey?: string) =>
    api.post<Appointment>('/appointments', data, {
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    }),

  update: (id: string, data: UpdateAppointmentData) =>
    api.put<Appointment>(`/appointments/${id}`, data),

  markCompleted: (id: string, data: CompleteAppointmentData, idempotencyKey?: string) =>
    api.post<Appointment>(`/appointments/${id}/mark-completed`, data, {
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    }),
};
```

---

## 6. Clinician Capability in Frontend

### How Frontend Knows User Is a Clinician

The frontend receives clinician capability information from:

1. **`GET /me` response** — includes `doctor_id`, `roles[]`, `doctor_profile_complete`
2. **Login response** — includes `doctor_id`, `roles[]`
3. **JWT claims** — `role` and `roles` claims

### Conditional Rendering

```tsx
// Check if user has clinician capability
const isClinician = user?.roles?.includes('doctor') || user?.doctor_id != null;

// Conditionally render clinician UI
{isClinician && (
  <Button onClick={openEncounter}>
    Open Encounter Workspace
  </Button>
)}
```

### Important Rules

- **Workspace context is NOT used for capability decisions** — a user in the doctor workspace may not be a clinician
- **Frontend does NOT make authorization decisions** — it relies on backend 403 responses
- **Route isolation enforces workspace scoping**, not capability scoping
- **Clinician-only UI elements** should be gated by `doctor_id` presence, not workspace

---

## 7. Container/Presentational Pattern

### Pages (Containers)

Pages fetch data and manage state:

```tsx
// pages/doctor/DoctorAppointmentsPage.tsx
function DoctorAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    appointmentsApi.list({ doctor_id: user.doctor_id })
      .then(res => setAppointments(res.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <GlobalLoader />;
  return <AppointmentList appointments={appointments} />;
}
```

### Components (Presentational)

Components render UI with props:

```tsx
// components/AppointmentList.tsx
function AppointmentList({ appointments }: { appointments: Appointment[] }) {
  return (
    <div className="space-y-4">
      {appointments.map(appt => (
        <AppointmentCard key={appt.id} appointment={appt} />
      ))}
    </div>
  );
}
```

---

## 8. Key Libraries & Tools

| Library | Purpose | Usage |
|---------|---------|-------|
| `react-router-dom` v7 | Routing | Route definitions, navigation |
| `axios` | HTTP client | API calls |
| `lucide-react` | Icons | UI icons throughout |
| `react-hot-toast` | Notifications | Toast messages |
| `framer-motion` | Animations | Page transitions, modals |
| `zod` | Validation | Form validation schemas |
| `class-variance-authority` | Component variants | Button variants, etc. |
| `tailwind-merge` | Class merging | Conditional Tailwind classes |
| `dayjs` | Date formatting | Date/time display |
| `shadcn/ui` | UI primitives | Dialog, Select, Switch, etc. |

---

## 9. Build & Development

### Commands

```bash
# Development
cd backend/frontend
npm run dev          # Vite dev server on :5173

# Type checking
npx tsc --noEmit     # TypeScript check without emitting

# Production build
npm run build        # Outputs to dist/

# Preview production build
npm run preview      # Preview server

# E2E tests
npx playwright test
```

### Environment Variables

```env
# backend/frontend/.env.local
VITE_API_URL=http://localhost:8000/api/v1
```

### Path Aliases

Configured in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Usage: `import { api } from '@/services/api'`
