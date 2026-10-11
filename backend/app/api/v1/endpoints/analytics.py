from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_staff
from app.db.session import get_db
from app.models.auth import User
from app.schemas.analytics import (
    CancellationsReportResponse,
    NoShowsReportResponse,
    OverviewKPIsResponse,
    PreAIBaselineResponse,
    UtilizationReportResponse,
    WaitingTimesReportResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/overview", response_model=OverviewKPIsResponse)
def get_operational_overview(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    department_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Get top-level hospital operational KPIs.
    Calculates waiting times, appointment utilization, cancellations, and no-show rates.
    Requires Staff authorization (ADMIN, DOCTOR, NURSE).
    """
    return AnalyticsService.get_overview_kpis(
        db=db,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )


@router.get("/waiting-times", response_model=WaitingTimesReportResponse)
def get_waiting_times_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Get detailed waiting times analysis across departments, doctors, and time slots.
    """
    return AnalyticsService.get_waiting_times_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/utilization", response_model=UtilizationReportResponse)
def get_utilization_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Get appointment slot capacity utilization, hourly density, and doctor loads.
    """
    return AnalyticsService.get_utilization_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/cancellations", response_model=CancellationsReportResponse)
def get_cancellations_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Get cancellation rate metrics across departments, weekdays, and common notes.
    """
    return AnalyticsService.get_cancellations_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/no-shows", response_model=NoShowsReportResponse)
def get_no_shows_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Get no-show rate breakdown by department, appointment hour, and patient demographics.
    """
    return AnalyticsService.get_no_shows_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/baseline", response_model=PreAIBaselineResponse)
def get_pre_ai_baseline(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Retrieve the formal Pre-AI Operational Baseline.
    Establishes benchmarks prior to ML and AI interventions.
    """
    return AnalyticsService.get_pre_ai_baseline(db=db)
