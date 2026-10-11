from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class OverviewKPIsResponse(BaseModel):
    total_appointments: int
    completed_count: int
    no_show_count: int
    cancelled_count: int
    scheduled_count: int
    no_show_rate_pct: float
    cancellation_rate_pct: float
    completion_rate_pct: float
    slot_utilization_pct: float
    avg_wait_time_minutes: float
    median_wait_time_minutes: float
    p90_wait_time_minutes: float
    avg_consultation_duration_minutes: float


class DepartmentWaitTimeItem(BaseModel):
    department: str
    completed_count: int
    avg_wait_mins: float
    median_wait_mins: float
    p90_wait_mins: float
    min_wait_mins: float
    max_wait_mins: float


class DoctorWaitTimeItem(BaseModel):
    doctor_name: str
    department: str
    completed_count: int
    avg_wait_mins: float
    p90_wait_mins: float


class TimeSlotWaitTimeItem(BaseModel):
    time_slot: str
    completed_count: int
    avg_wait_mins: float
    p90_wait_mins: float


class WaitingTimesReportResponse(BaseModel):
    by_department: List[DepartmentWaitTimeItem]
    by_doctor: List[DoctorWaitTimeItem]
    by_time_slot: List[TimeSlotWaitTimeItem]


class HourlyUtilizationItem(BaseModel):
    hour: int
    total_booked: int
    completed: int
    no_shows: int
    fulfillment_pct: Optional[float] = None


class DayOfWeekUtilizationItem(BaseModel):
    day_name: str
    day_number: int
    total_appointments: int
    completed: int
    avg_wait_mins: Optional[float] = None


class DoctorUtilizationItem(BaseModel):
    doctor_name: str
    department: str
    total_scheduled: int
    completed: int
    utilization_pct: Optional[float] = None


class UtilizationReportResponse(BaseModel):
    hourly_distribution: List[HourlyUtilizationItem]
    day_of_week_distribution: List[DayOfWeekUtilizationItem]
    doctor_utilization: List[DoctorUtilizationItem]


class DepartmentCancellationItem(BaseModel):
    department: str
    total_booked: int
    cancelled_count: int
    cancellation_rate_pct: Optional[float] = None


class DayOfWeekCancellationItem(BaseModel):
    day_name: str
    day_number: int
    total_booked: int
    cancelled_count: int
    cancellation_rate_pct: Optional[float] = None


class CancellationReasonItem(BaseModel):
    reason_note: str
    occurrences: int


class CancellationsReportResponse(BaseModel):
    by_department: List[DepartmentCancellationItem]
    by_day_of_week: List[DayOfWeekCancellationItem]
    common_reasons: List[CancellationReasonItem]


class DepartmentNoShowItem(BaseModel):
    department: str
    total_appointments: int
    completed_count: int
    no_show_count: int
    no_show_rate_pct: Optional[float] = None


class HourlyNoShowItem(BaseModel):
    hour: int
    total: int
    no_shows: int
    no_show_rate_pct: Optional[float] = None


class GenderNoShowItem(BaseModel):
    gender: str
    total: int
    no_shows: int
    no_show_rate_pct: Optional[float] = None


class NoShowsReportResponse(BaseModel):
    by_department: List[DepartmentNoShowItem]
    by_hour: List[HourlyNoShowItem]
    by_gender: List[GenderNoShowItem]


class PreAIBaselineResponse(BaseModel):
    baseline_definition: str
    established_at: str
    cohort_sample_size: int
    benchmarks: Dict[str, float]
    operational_target_with_ai: Dict[str, float]
    status: str
