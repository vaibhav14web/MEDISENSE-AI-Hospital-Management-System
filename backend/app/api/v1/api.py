from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    appointments,
    auth,
    departments,
    doctors,
    patients,
    ml_no_show,
    imaging,
    llm,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Intelligence"])
api_router.include_router(ml_no_show.router, prefix="/ml/no-show", tags=["Machine Learning"])
api_router.include_router(imaging.router, prefix="/imaging", tags=["Medical Imaging & DL"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM & Clinical Intelligence"])
