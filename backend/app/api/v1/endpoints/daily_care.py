"""
Daily Care Dashboard API Endpoints — Phase P3 Daily Care Dashboard + Adherence Experience.

Architecture:
  These endpoints compose existing domain data into a patient-friendly
  Today's Care Dashboard. They enforce strict patient-scoped access.

  DailyCareDashboardAggregate is a READ-ONLY aggregate.
  It does NOT create new database tables or duplicate source-of-truth data.

Authorization:
  - Patient-only access (non-patients receive 403)
  - Tenant isolation via existing data_scope patterns
  - Patient identity is resolved from current_user (never from request params)
  - Prescription data is NEVER mutated through these endpoints
  - Adherence actions affect tracking ONLY

TODO: Phase 4 — Push notification hooks
TODO: Phase 4 — Background reminder hooks
TODO: Phase 4 — OS notification integration hooks
TODO: Phase 4 — Wearable integration hooks
TODO: Phase 4 — Apple Health / Google Fit sync hooks
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_scoped_tenant_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.daily_care import DailyCareDashboardAggregate
from app.services import daily_care_service
from app.services.exceptions import ForbiddenError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/patient/daily-care",
    tags=["patient-daily-care"],
)


@router.get("", response_model=DailyCareDashboardAggregate)
def get_daily_care_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID | None = Depends(get_optional_scoped_tenant_id),
) -> DailyCareDashboardAggregate:
    """
    Get the full Daily Care Dashboard for the authenticated patient.

    Returns a comprehensive daily care dashboard with 5 sections:
    1. MedicinesDueToday — medications grouped by due now / upcoming / overdue / completed
    2. UpcomingCare — next appointment, follow-ups, unread communications
    3. ContinueCare — recent doctors, recent prescriptions
    4. HealthTimelinePreview — last 3 encounter preview cards
    5. QuickActions — action shortcuts (book appointment, view medicines, etc.)

    CRITICAL:
    - Patient access is strictly scoped to their own data
    - Prescription data is NEVER mutated through this aggregate
    - Adherence actions affect tracking ONLY
    - No shadow adherence systems are created
    """
    try:
        return daily_care_service.get_daily_care_dashboard(db, current_user)
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
