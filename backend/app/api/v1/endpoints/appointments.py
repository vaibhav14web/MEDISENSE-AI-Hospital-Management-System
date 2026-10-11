from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, require_staff
from app.db.session import get_db
from app.models.auth import User
from app.models.clinical import Patient
from app.models.hospital import Appointment, Doctor
from app.schemas.hospital import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)

router = APIRouter()

VALID_STATUSES = {"scheduled", "completed", "cancelled", "no_show"}


@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    doctor_id: Optional[UUID] = None,
    patient_id: Optional[UUID] = None,
    appointment_status: Optional[str] = Query(None, alias="status"),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    List appointments with filters.
    Patients are scoped to their own appointments unless staff.
    """
    query = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.department),
        )
    )

    user_role = current_user.role.name.upper() if current_user.role else ""

    # Scoping for patients
    if user_role == "PATIENT":
        patient_rec = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_rec:
            return []
        query = query.filter(Appointment.patient_id == patient_rec.id)
    elif patient_id:
        query = query.filter(Appointment.patient_id == patient_id)

    # Scoping for doctors
    if user_role == "DOCTOR":
        doc_rec = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc_rec:
            return []
        query = query.filter(Appointment.doctor_id == doc_rec.id)
    elif doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)

    if appointment_status:
        query = query.filter(Appointment.status == appointment_status.lower())

    if from_date:
        query = query.filter(Appointment.scheduled_at >= from_date)

    if to_date:
        query = query.filter(Appointment.scheduled_at <= to_date)

    return query.order_by(Appointment.scheduled_at.desc()).offset(skip).limit(limit).all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get appointment by ID."""
    appt = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.department),
        )
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    user_role = current_user.role.name.upper() if current_user.role else ""
    if user_role == "PATIENT":
        patient_rec = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_rec or appt.patient_id != patient_rec.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return appt


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appt_in: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Schedule a new appointment.
    Verifies patient and doctor exist, and validates patient ownership if called by PATIENT role.
    """
    # Check patient
    patient = db.query(Patient).filter(Patient.id == appt_in.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Patient role authorization check
    user_role = current_user.role.name.upper() if current_user.role else ""
    if user_role == "PATIENT" and patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot schedule appointments for other patients")

    # Check doctor
    doctor = db.query(Doctor).filter(Doctor.id == appt_in.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Conflict check: doctor cannot have two active appointments at the exact same slot
    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appt_in.doctor_id,
            Appointment.scheduled_at == appt_in.scheduled_at,
            Appointment.status != "cancelled",
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor already has an active appointment scheduled at this time",
        )

    appt = Appointment(
        patient_id=appt_in.patient_id,
        doctor_id=appt_in.doctor_id,
        scheduled_at=appt_in.scheduled_at,
        status="scheduled",
        reason=appt_in.reason,
        notes=appt_in.notes,
    )
    db.add(appt)
    db.commit()
    return (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.department),
        )
        .filter(Appointment.id == appt.id)
        .first()
    )


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: UUID,
    status_update: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """
    Update appointment status (scheduled, completed, cancelled, no_show).
    Supports capturing started_at and ended_at timestamps for operational intelligence.
    Requires Staff (ADMIN, DOCTOR, NURSE).
    """
    clean_status = status_update.status.lower().strip()
    if clean_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{clean_status}'. Must be one of {list(VALID_STATUSES)}",
        )

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    user_role = current_user.role.name.upper() if current_user.role else ""
    # Doctors can only update status for their own consultations
    if user_role == "DOCTOR":
        doc_rec = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc_rec or appt.doctor_id != doc_rec.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update appointment statuses for their own assigned consultations",
            )

    appt.status = clean_status

    if status_update.started_at is not None:
        appt.started_at = status_update.started_at
    elif clean_status == "completed" and appt.started_at is None:
        appt.started_at = appt.scheduled_at

    if status_update.ended_at is not None:
        appt.ended_at = status_update.ended_at
    elif clean_status == "completed" and appt.ended_at is None:
        base_start = appt.started_at or appt.scheduled_at
        appt.ended_at = base_start + timedelta(minutes=20)

    # Maintain database invariant: ended_at >= started_at
    if appt.started_at and appt.ended_at and appt.ended_at < appt.started_at:
        appt.ended_at = appt.started_at + timedelta(minutes=15)

    if status_update.notes:
        appt.notes = f"{appt.notes}\n{status_update.notes}" if appt.notes else status_update.notes

    db.commit()
    return (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.department),
        )
        .filter(Appointment.id == appointment_id)
        .first()
    )


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment_details(
    appointment_id: UUID,
    appt_in: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update or reschedule appointment details with strict RBAC integrity checks."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    user_role = current_user.role.name.upper() if current_user.role else ""

    # Scoping & authorization checks
    if user_role == "PATIENT":
        patient_rec = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_rec or appt.patient_id != patient_rec.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Patients cannot mark appointments completed or no_show
        if appt_in.status and appt_in.status.lower() not in ("cancelled", "scheduled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients are only permitted to cancel or reschedule appointments",
            )
    elif user_role == "DOCTOR":
        doc_rec = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc_rec or appt.doctor_id != doc_rec.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only modify their own assigned consultations",
            )
    elif user_role not in ("ADMIN", "NURSE"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized action")

    # If rescheduling, check for slot conflicts
    target_doctor_id = appt.doctor_id
    target_time = appt_in.scheduled_at or appt.scheduled_at
    if appt_in.scheduled_at and appt_in.scheduled_at != appt.scheduled_at:
        conflict = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == target_doctor_id,
                Appointment.scheduled_at == target_time,
                Appointment.id != appointment_id,
                Appointment.status != "cancelled",
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor already has an active appointment scheduled at this time",
            )

    for field, val in appt_in.model_dump(exclude_unset=True).items():
        if field == "status" and val:
            if val.lower() not in VALID_STATUSES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {val}")
            setattr(appt, field, val.lower())
        else:
            setattr(appt, field, val)

    db.commit()
    return (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.department),
        )
        .filter(Appointment.id == appointment_id)
        .first()
    )
