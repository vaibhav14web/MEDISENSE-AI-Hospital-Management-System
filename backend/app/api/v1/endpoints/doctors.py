from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, require_admin, require_doctor
from app.db.session import get_db
from app.models.auth import User
from app.models.hospital import Department, Doctor, DoctorAvailability
from app.schemas.hospital import (
    DoctorAvailabilityCreate,
    DoctorAvailabilityResponse,
    DoctorCreate,
    DoctorResponse,
    DoctorUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[DoctorResponse])
def list_doctors(
    department_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List doctors with department filtering."""
    query = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.department))
    )
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get doctor profile by ID."""
    doc = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.department))
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doc


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    doc_in: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Any:
    """Create a new doctor record (Requires ADMIN role)."""
    user = db.query(User).filter(User.id == doc_in.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")

    existing_doc = db.query(Doctor).filter(Doctor.user_id == doc_in.user_id).first()
    if existing_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile already exists for this user")

    existing_license = db.query(Doctor).filter(Doctor.license_number == doc_in.license_number).first()
    if existing_license:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="License number is already registered")

    if doc_in.department_id:
        dept = db.query(Department).filter(Department.id == doc_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    doc = Doctor(
        user_id=doc_in.user_id,
        department_id=doc_in.department_id,
        license_number=doc_in.license_number,
        specialization=doc_in.specialization,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doctor_id}/availability", response_model=List[DoctorAvailabilityResponse])
def get_doctor_availability(
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get doctor weekly availability schedule."""
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    return (
        db.query(DoctorAvailability)
        .filter(DoctorAvailability.doctor_id == doctor_id, DoctorAvailability.is_active == True)
        .order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time)
        .all()
    )


@router.post("/{doctor_id}/availability", response_model=DoctorAvailabilityResponse, status_code=status.HTTP_201_CREATED)
def set_doctor_availability(
    doctor_id: UUID,
    avail_in: DoctorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
) -> Any:
    """Set doctor weekly availability schedule (Requires DOCTOR or ADMIN role)."""
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # If DOCTOR, verify they are updating their own availability
    if current_user.role.name.upper() == "DOCTOR" and doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctors can only configure their own availability schedule",
        )

    avail = DoctorAvailability(
        doctor_id=doctor_id,
        day_of_week=avail_in.day_of_week,
        start_time=avail_in.start_time,
        end_time=avail_in.end_time,
        slot_duration_minutes=avail_in.slot_duration_minutes,
        is_active=avail_in.is_active,
        effective_start_date=avail_in.effective_start_date,
        effective_end_date=avail_in.effective_end_date,
    )
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail
