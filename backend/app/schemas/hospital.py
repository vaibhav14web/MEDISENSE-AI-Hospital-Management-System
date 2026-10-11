from datetime import date, datetime, time
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ===================== Department Schemas =====================
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ===================== Doctor Availability Schemas =====================
class DoctorAvailabilityBase(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Sunday, 1=Monday, ..., 6=Saturday")
    start_time: time
    end_time: time
    slot_duration_minutes: int = 15
    is_active: bool = True
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass


class DoctorAvailabilityResponse(DoctorAvailabilityBase):
    id: UUID
    doctor_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ===================== Doctor Schemas =====================
class DoctorBase(BaseModel):
    department_id: Optional[UUID] = None
    license_number: str
    specialization: Optional[str] = None


class DoctorCreate(DoctorBase):
    user_id: UUID


class DoctorUpdate(BaseModel):
    department_id: Optional[UUID] = None
    specialization: Optional[str] = None


class DoctorUserSummary(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: Optional[str] = None

    class Config:
        from_attributes = True


class DoctorResponse(DoctorBase):
    id: UUID
    user_id: UUID
    user: Optional[DoctorUserSummary] = None
    department: Optional[DepartmentResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===================== Appointment Schemas =====================
class AppointmentBase(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    scheduled_at: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None  # scheduled, completed, cancelled, no_show
    reason: Optional[str] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class AppointmentStatusUpdate(BaseModel):
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: UUID
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    doctor: Optional[DoctorResponse] = None

    class Config:
        from_attributes = True
