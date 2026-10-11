from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, require_staff
from app.db.session import get_db
from app.models.auth import User
from app.models.clinical import Patient
from app.schemas.clinical import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter()


@router.get("/", response_model=List[PatientResponse])
def list_patients(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Any:
    """List registered patients with pagination (Requires Hospital Staff: ADMIN, DOCTOR, NURSE)."""
    return (
        db.query(Patient)
        .options(joinedload(Patient.user))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get patient profile by ID. Patients may view their own; staff may view any."""
    patient = (
        db.query(Patient)
        .options(joinedload(Patient.user))
        .filter(Patient.id == patient_id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    user_role = current_user.role.name.upper() if current_user.role else ""
    if user_role == "PATIENT" and patient.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients can only access their own medical profile",
        )

    return patient


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a patient profile for a user."""
    user = db.query(User).filter(User.id == patient_in.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")

    user_role = current_user.role.name.upper() if current_user.role else ""
    if user_role == "PATIENT" and current_user.id != patient_in.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a profile for another user",
        )

    existing = db.query(Patient).filter(Patient.user_id == patient_in.user_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient profile already exists")

    patient = Patient(
        user_id=patient_in.user_id,
        date_of_birth=patient_in.date_of_birth,
        gender=patient_in.gender,
        blood_group=patient_in.blood_group,
        phone=patient_in.phone,
        address=patient_in.address,
        emergency_contact_name=patient_in.emergency_contact_name,
        emergency_contact_phone=patient_in.emergency_contact_phone,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: UUID,
    patient_in: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update patient demographic details."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    user_role = current_user.role.name.upper() if current_user.role else ""
    if user_role == "PATIENT" and patient.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients can only edit their own profile",
        )

    for field, val in patient_in.model_dump(exclude_unset=True).items():
        setattr(patient, field, val)

    db.commit()
    db.refresh(patient)
    return patient
