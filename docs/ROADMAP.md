# Roadmap

> **Last updated:** May 13, 2026
> **Status:** Active development — multi-tenant healthcare platform

---

## 1. Implemented Features

### Core Platform
- [x] Multi-tenant architecture with tenant isolation
- [x] JWT authentication with role-based access
- [x] User registration and login
- [x] Tenant management (create, configure)
- [x] Super admin cross-tenant oversight
- [x] Capability-based authorization (clinician capability)
- [x] Workspace-based frontend routing
- [x] Route isolation by workspace

### Patient Management
- [x] Global patient architecture (patients are tenant-independent)
- [x] Patient CRUD with search
- [x] Patient clinical notes (doctor-facing)
- [x] Patient trust relationships and caregiver access
- [x] Patient communication preferences
- [x] Patient documents upload

### Doctor Management
- [x] Doctor CRUD with tenant scoping
- [x] Doctor creation with login (admin/super_admin)
- [x] Doctor availability windows
- [x] Bookable slots
- [x] Doctor-patient detail with activity timeline
- [x] Doctor verification logs

### Appointment & Encounter
- [x] Appointment scheduling with idempotency
- [x] Appointment status management (scheduled, checked_in, in_consultation, completed, cancelled)
- [x] Encounter aggregate (appointment + patient + doctor + vitals + notes + bills + inventory)
- [x] Clinical notes, diagnosis, treatment summary
- [x] Vitals recording (BP, pulse, temperature, SpO2, respiratory rate, weight, height)
- [x] Appointment completion with idempotency
- [x] Appointment invariant enforcement (doctor/tenant alignment)

### Queue Management
- [x] Clinic queue entry (waiting, in_consultation, completed, cancelled)
- [x] Front desk check-in
- [x] Queue status transitions

### Billing
- [x] Bill creation (with optional appointment linkage)
- [x] Bill payment (pending → paid)
- [x] Billing invariants (tenant alignment)

### Inventory & Procurement
- [x] Inventory management (items, stock levels)
- [x] Clinical inventory consumption during encounters
- [x] Supplier management
- [x] Purchase orders (draft → ordered → received → cancelled)
- [x] Procurement valuation

### Patient Workspace
- [x] Patient home dashboard
- [x] Health timeline (encounters, vitals, medications)
- [x] Medication schedules
- [x] Communication center (preferences, reminders)
- [x] Vitals history with trends
- [x] Family hub (dependents, caregiver access)
- [x] Emergency profile
- [x] Visit preparation checklist
- [x] Care continuity summary
- [x] Document management

### Clinic Operations
- [x] Operational alerts (critical, warning, info)
- [x] Staff tasks (pending → in_progress → completed)
- [x] Activity feed
- [x] Doctor operations view

### Notifications & Communications
- [x] Notification templates
- [x] Notification providers (email, SMS, push)
- [x] Reminder service
- [x] Patient communication preferences

### Tenant Branding
- [x] Tenant organization profile
- [x] Tenant branding (logo, colors, theme)
- [x] Branding API endpoints

### Reporting
- [x] Appointment reports
- [x] Revenue reports
- [x] Inventory reports
- [x] Export service

### Integrity & Audit
- [x] Integrity scan service (cross-tenant and per-tenant)
- [x] Structured audit logging
- [x] Idempotency for all CREATE operations
- [x] Appointment invariant guard

### Frontend
- [x] Workspace-based architecture (6 workspaces)
- [x] shadcn/ui component library
- [x] Tailwind CSS styling
- [x] Responsive design (mobile, tablet, desktop)
- [x] Framer Motion animations
- [x] Zod form validation
- [x] Axios API client with interceptors

### Testing
- [x] Backend pytest suite (SQLite default, PostgreSQL optional)
- [x] Frontend Playwright E2E tests
- [x] Test factories
- [x] PostgreSQL-only test marker

---

## 2. In Progress

### Clinic Operations & Staff Workflows (Part 1)
- [ ] Extended appointment statuses (checked_in, in_consultation)
- [ ] ClinicQueueEntry model and migration
- [ ] Queue service and front desk service
- [ ] Nurse workflow service
- [ ] Frontend queue management UI
- [ ] Frontend front desk dashboard
- [ ] Test clinic operations

### Backend Workspace Context Injection (Part 2-4)
- [ ] Update services to accept `active_workspace`
- [ ] Use `is_elevated_workspace_access()` for workspace-aware elevation
- [ ] Inject `get_active_workspace` into all relevant endpoints
- [ ] Validation (type-check, build, test)

### SPO2 Model Mismatch Fix
- [ ] Add `spo2` column to `AppointmentVitals` model
- [ ] Create migration `z8_appointment_vitals_spo2.py`

---

## 3. Planned Features

### Short Term (Next 2-4 Weeks)

#### Nurse Workflows
- [ ] Nurse queue view
- [ ] Pre-consultation vitals recording
- [ ] Room assignment
- [ ] Nurse authorization (has_nurse_capability)

#### Enhanced Queue Management
- [ ] Real-time queue updates (WebSocket)
- [ ] Estimated wait time calculation
- [ ] Priority queue (emergency cases)
- [ ] Multi-room support

#### Prescription Enhancements
- [ ] Drug interaction checking
- [ ] Dosage calculation
- [ ] E-prescription generation
- [ ] Prescription refill workflow

#### Patient Portal Enhancements
- [ ] Online appointment booking (self-service)
- [ ] Appointment reminders (email/SMS)
- [ ] Telemedicine link integration
- [ ] Patient feedback and ratings

### Medium Term (1-3 Months)

#### Advanced Clinical Features
- [ ] Lab test ordering and results
- [ ] Imaging orders and results
- [ ] Immunization tracking
- [ ] Allergy and intolerance management
- [ ] Problem list / medical history
- [ ] Clinical decision support rules

#### Financial & Revenue Cycle
- [ ] Insurance claim management
- [ ] Payment gateway integration
- [ ] Revenue cycle analytics
- [ ] Patient payment portal
- [ ] Tax invoice generation

#### Inventory & Supply Chain
- [ ] Automated reorder points
- [ ] Barcode/RFID scanning
- [ ] Expiry date tracking
- [ ] Multi-warehouse support
- [ ] Inventory valuation (FIFO, weighted average)

#### Analytics & Reporting
- [ ] Custom report builder
- [ ] Dashboard widgets (configurable)
- [ ] Export to PDF/Excel
- [ ] Data visualization (charts, graphs)
- [ ] Operational KPIs

### Long Term (3-6 Months)

#### Interoperability
- [ ] HL7 FHIR integration
- [ ] EHR data exchange
- [ ] National health ID integration
- [ ] Pharmacy system integration
- [ ] Laboratory system integration

#### Advanced Multi-Tenancy
- [ ] Tenant sharding
- [ ] Tenant-specific feature flags
- [ ] White-label support
- [ ] Tenant migration tools

#### Security & Compliance
- [ ] HIPAA compliance audit
- [ ] Audit trail for all PHI access
- [ ] Data encryption at rest
- [ ] Session management (refresh tokens)
- [ ] Rate limiting
- [ ] IP whitelisting

#### Mobile Applications
- [ ] React Native patient app
- [ ] React Native doctor app
- [ ] Offline support
- [ ] Push notifications

#### Infrastructure
- [ ] CI/CD pipeline improvements
- [ ] Docker containerization
- [ ] Kubernetes orchestration
- [ ] Database read replicas
- [ ] CDN for static assets
- [ ] Monitoring and alerting (Datadog, Sentry)

---

## 4. Technical Debt & Improvements

### Backend
- [ ] Migrate from SQLAlchemy 1.x patterns to 2.0 Mapped style (in progress)
- [ ] Add pagination to all list endpoints
- [ ] Implement refresh token rotation
- [ ] Add request rate limiting
- [ ] Improve error boundary handling
- [ ] Add request ID tracing
- [ ] Implement database connection pooling tuning

### Frontend
- [ ] Add loading skeletons for all pages
- [ ] Improve accessibility (ARIA labels, keyboard navigation)
- [ ] Add error boundaries for all route segments
- [ ] Implement proper form error display
- [ ] Add unit tests for hooks and services
- [ ] Reduce bundle size (code splitting, lazy loading)
- [ ] Add Storybook for component documentation

### Testing
- [ ] Increase backend test coverage to >80%
- [ ] Add frontend unit tests (Vitest)
- [ ] Add integration tests for critical workflows
- [ ] Add performance/load tests
- [ ] Add security tests (OWASP ZAP)

### Documentation
- [x] Architecture documentation
- [x] Authorization model documentation
- [x] Multi-tenancy documentation
- [x] Clinical workflow documentation
- [x] API conventions documentation
- [x] Frontend structure documentation
- [x] Migration guide
- [x] Deployment guide
- [ ] API reference (auto-generated from OpenAPI)
- [ ] Developer setup guide
- [ ] Contribution guidelines

---

## 5. Version History

| Version | Date | Highlights |
|---------|------|------------|
| v0.1 | Early 2026 | Initial schema, basic CRUD |
| v0.2 | Mar 2026 | Multi-tenancy, JWT auth, appointment management |
| v0.3 | Apr 2026 | Doctor workflows, patient timeline, clinical notes |
| v0.4 | Apr 2026 | Encounter workspace, inventory consumption, billing |
| v0.5 | May 2026 | Patient workspace, notifications, branding, reporting |
| v0.6 | May 2026 | Queue management, clinic operations, procurement |
| v0.7 | May 2026 | Capability-based authorization, workspace refactor |

---

## 6. Key Architectural Decisions

### Made
1. **Appointment as encounter anchor** — No separate Visit table
2. **Global patient architecture** — `patient.tenant_id` is always NULL
3. **Resource ownership is authoritative** — Not frontend tenant IDs
4. **Capability-based clinical auth** — Not role-based for doctor actions
5. **Workspace-independent clinical permissions** — Workspace is UI context only
6. **Idempotency for all CREATE operations** — Safe retries
7. **Additive migrations only** — Never drop columns/tables

### Under Consideration
1. **WebSocket for real-time updates** — Queue, notifications
2. **Event sourcing for audit trail** — Complete history of changes
3. **CQRS for reporting** — Separate read models for analytics
4. **Microservices extraction** — Billing, notifications as separate services
5. **GraphQL for patient portal** — Flexible data fetching
