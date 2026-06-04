from fastapi import APIRouter

from app.api.v1.endpoints import (
    appointment,
    auth,
    billing,
    branding,
    clinic_operations,
    clinic_queue,
    communications,
    daily_care,
    dashboard,
    doctor,
    doctor_profile,
    documents,
    encounter,
    front_desk,
    health,
    inventory,
    medication_schedule,
    patient,
    patient_communication,
    patient_workspace,
    public,
    reporting,
    tenant,
    users,
)



api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patient.router)
api_router.include_router(tenant.router)
api_router.include_router(doctor.router)
api_router.include_router(doctor_profile.router)
api_router.include_router(appointment.router)
api_router.include_router(billing.router)
api_router.include_router(inventory.router)
api_router.include_router(encounter.router)
api_router.include_router(reporting.router)
api_router.include_router(dashboard.router, prefix="/dashboard")
api_router.include_router(dashboard.admin_router, prefix="/admin")
api_router.include_router(documents.router)
api_router.include_router(branding.router)
api_router.include_router(communications.router)
api_router.include_router(patient_workspace.router)
api_router.include_router(patient_communication.router)
api_router.include_router(medication_schedule.router)
api_router.include_router(daily_care.router)
api_router.include_router(clinic_queue.router)
api_router.include_router(front_desk.router)
api_router.include_router(public.router)
api_router.include_router(clinic_operations.router)


