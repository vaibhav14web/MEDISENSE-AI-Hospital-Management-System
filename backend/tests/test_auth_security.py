from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import SessionLocal
from app.models.auth import Role, User
from app.models.clinical import Patient
from app.models.hospital import Appointment, Doctor, Department

client = TestClient(app)


# ==============================================================================
# Helper Functions
# ==============================================================================
def get_token(email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Failed login for {email}: {resp.text}"
    return resp.json()["access_token"]


# ==============================================================================
# 1. Authentication Integrity & Cryptographic Security
# ==============================================================================
def test_sec_01_verify_password_rejects_backdoors():
    """Verify password check rejects known demo strings if hash is not matching bcrypt."""
    assert not verify_password("Demo@123", "DEMO_HASH_ONLY")
    assert not verify_password("password123", "DEMO_HASH_ONLY")
    assert not verify_password("", "valid_hash")
    assert not verify_password("valid_password", "")


def test_sec_02_password_length_enforced_on_registration():
    """Verify registration rejects passwords shorter than 8 characters."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"short_pw_{uuid.uuid4().hex[:6]}@example.com",
            "password": "123",  # Too short (< 8 chars)
            "first_name": "Short",
            "last_name": "Pass",
            "role_name": "PATIENT",
        },
    )
    assert resp.status_code == 422  # Unprocessable Entity (Pydantic validation)


def test_sec_03_expired_jwt_rejected():
    """Verify expired JWT tokens are rejected with 401 Unauthorized."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    
    # Generate token that expired 1 hour ago
    expired_token = create_access_token(
        subject=str(uuid.uuid4()),
        role="ADMIN",
        expires_delta=timedelta(hours=-1),
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "Invalid or expired access token" in resp.json()["detail"]


def test_sec_04_tampered_jwt_claims_rejected():
    """Verify tokens signed with wrong secret or malformed payload are rejected."""
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.real.jwt"})
    assert resp.status_code == 401


def test_sec_05_inactive_user_cannot_login_or_use_tokens():
    """Verify deactivated user accounts cannot log in and active tokens are immediately blocked."""
    db = SessionLocal()
    try:
        # Create a deactivated user
        role = db.query(Role).filter(Role.name == "PATIENT").first()
        deactivated_email = f"deactivated_{uuid.uuid4().hex[:6]}@example.com"
        deact_user = User(
            email=deactivated_email,
            password_hash=get_password_hash("ActivePassword@123"),
            first_name="Deactivated",
            last_name="User",
            role_id=role.id,
            is_active=False,
        )
        db.add(deact_user)
        db.commit()
        db.refresh(deact_user)

        # 1. Login attempt fails with 403 Forbidden
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": deactivated_email, "password": "ActivePassword@123"},
        )
        assert login_resp.status_code == 403
        assert "deactivated" in login_resp.json()["detail"]

        # 2. Even with a signed token for this subject, get_current_user must reject with 401
        token = create_access_token(subject=str(deact_user.id), role="PATIENT")
        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 401
    finally:
        db.close()


# ==============================================================================
# 2. Privilege Escalation Prevention
# ==============================================================================
def test_sec_06_public_registration_cannot_create_admin():
    """Verify public registration cannot escalate privileges to ADMIN."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"attacker_admin_{uuid.uuid4().hex[:6]}@example.com",
            "password": "AttackerPass@123",
            "first_name": "Attacker",
            "last_name": "Admin",
            "role_name": "ADMIN",
        },
    )
    assert resp.status_code == 403
    assert "Public registration is restricted to PATIENT role" in resp.json()["detail"]


def test_sec_07_public_registration_cannot_create_doctor_or_nurse():
    """Verify public registration cannot escalate privileges to DOCTOR or NURSE."""
    for forbidden_role in ["DOCTOR", "NURSE"]:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"attacker_{forbidden_role.lower()}_{uuid.uuid4().hex[:6]}@example.com",
                "password": "AttackerPass@123",
                "first_name": "Attacker",
                "last_name": "Staff",
                "role_name": forbidden_role,
            },
        )
        assert resp.status_code == 403


def test_sec_08_admin_can_create_staff_users():
    """Verify administrator can create staff users via dedicated /auth/staff endpoint."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    staff_email = f"staff.doc.{uuid.uuid4().hex[:6]}@hospital.com"

    # Non-admin cannot create staff
    patient_token = get_token("patient@hospital.com", "Patient@123")
    forbidden_resp = client.post(
        "/api/v1/auth/staff",
        json={
            "email": staff_email,
            "password": "DoctorPass@123",
            "first_name": "Staff",
            "last_name": "Doc",
            "role_name": "DOCTOR",
        },
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert forbidden_resp.status_code == 403

    # Admin successfully creates staff
    staff_resp = client.post(
        "/api/v1/auth/staff",
        json={
            "email": staff_email,
            "password": "DoctorPass@123",
            "first_name": "Staff",
            "last_name": "Doc",
            "role_name": "DOCTOR",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert staff_resp.status_code == 201
    assert staff_resp.json()["role"]["name"] == "DOCTOR"


# ==============================================================================
# 3. RBAC Scoping & Clinical Boundary Controls
# ==============================================================================
def test_sec_09_patient_cannot_access_analytics():
    """Ensure patients are forbidden from viewing operational analytics."""
    patient_token = get_token("patient@hospital.com", "Patient@123")
    endpoints = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/waiting-times",
        "/api/v1/analytics/utilization",
        "/api/v1/analytics/cancellations",
        "/api/v1/analytics/no-shows",
        "/api/v1/analytics/baseline",
    ]
    for ep in endpoints:
        resp = client.get(ep, headers={"Authorization": f"Bearer {patient_token}"})
        assert resp.status_code == 403, f"Endpoint {ep} allowed patient access!"


def test_sec_10_patient_cannot_access_other_patient_profile():
    """Ensure patients cannot access other patients' medical records (IDOR protection)."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    patient_token = get_token("patient@hospital.com", "Patient@123")

    # Get list of patients as admin
    patients = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert len(patients) >= 2

    # Find patient record NOT belonging to patient@hospital.com
    my_profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {patient_token}"}).json()
    other_patient = next((p for p in patients if p["user_id"] != my_profile["id"]), None)
    assert other_patient is not None

    # Patient attempting to access other patient's record is blocked
    idor_resp = client.get(
        f"/api/v1/patients/{other_patient['id']}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert idor_resp.status_code == 403
    assert "Patients can only access their own medical profile" in idor_resp.json()["detail"]


def test_sec_11_patient_cannot_schedule_for_other_patient():
    """Ensure a patient cannot schedule an appointment under another patient's ID."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    patient_token = get_token("patient@hospital.com", "Patient@123")

    patients = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    doctors = client.get("/api/v1/doctors/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    my_profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {patient_token}"}).json()
    
    other_patient = next((p for p in patients if p["user_id"] != my_profile["id"]), None)
    assert other_patient is not None

    target_time = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    resp = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": other_patient["id"],
            "doctor_id": doctors[0]["id"],
            "scheduled_at": target_time,
            "reason": "Unauthorized booking",
        },
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp.status_code == 403
    assert "Cannot schedule appointments for other patients" in resp.json()["detail"]


def test_sec_12_patient_cannot_mark_appointment_completed():
    """Ensure patients cannot exploit PUT /appointments to mark consultations completed."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    patient_token = get_token("patient@hospital.com", "Patient@123")

    # Get patient's own patient record
    my_profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {patient_token}"}).json()
    patients = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    my_patient = next((p for p in patients if p["user_id"] == my_profile["id"]), None)
    assert my_patient is not None

    doctors = client.get("/api/v1/doctors/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    
    # Book an appointment as patient
    target_time = (datetime.now(timezone.utc) + timedelta(days=25)).isoformat()
    booking = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": my_patient["id"],
            "doctor_id": doctors[0]["id"],
            "scheduled_at": target_time,
            "reason": "Legitimate checkup",
        },
        headers={"Authorization": f"Bearer {patient_token}"},
    ).json()

    # Attempt to mark it completed as patient must be blocked
    exploit_resp = client.put(
        f"/api/v1/appointments/{booking['id']}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert exploit_resp.status_code == 403
    assert "only permitted to cancel or reschedule" in exploit_resp.json()["detail"]


def test_sec_13_doctor_cannot_tamper_with_other_doctor_appointments():
    """Ensure a doctor cannot update statuses on another physician's assigned appointment."""
    admin_token = get_token("admin@hospital.com", "Admin@123")
    doc_token = get_token("doctor@hospital.com", "Doctor@123")

    doctors = client.get("/api/v1/doctors/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    patients = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {admin_token}"}).json()
    doc_profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {doc_token}"}).json()

    # Find doctor record NOT belonging to logged in doctor
    other_doctor = next((d for d in doctors if d["user_id"] != doc_profile["id"]), None)
    assert other_doctor is not None

    # Admin books appointment with the other doctor
    target_time = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    booking = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": patients[0]["id"],
            "doctor_id": other_doctor["id"],
            "scheduled_at": target_time,
            "reason": "Consultation with other doctor",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    # Logged-in doctor tries to update status of the other doctor's appointment
    patch_resp = client.patch(
        f"/api/v1/appointments/{booking['id']}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert patch_resp.status_code == 403
    assert "Doctors can only update appointment statuses for their own assigned consultations" in patch_resp.json()["detail"]


def test_sec_14_production_secret_key_guard_enforced():
    """Verify Settings raises ValueError when production mode is set with default SECRET_KEY."""
    from app.core.config import Settings
    
    # 1. Insecure default secret in production should fail
    insecure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="ai_hms_super_secret_jwt_key_development_2026_change_in_production",
    )
    with pytest.raises(ValueError, match="FATAL SECURITY CONFIGURATION ERROR"):
        insecure_settings.validate_production_security()

    # 2. Strong custom secret in production should pass
    secure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_strong_random_production_secret_key_abcdef123456789",
    )
    # Should not raise
    secure_settings.validate_production_security()


def test_sec_15_dynamic_ml_thresholds_configurable():
    """Verify ML inference thresholds can be customized dynamically per clinic policy."""
    from models.no_show.predict import NoShowPredictor
    
    predictor = NoShowPredictor(high_threshold=0.30, medium_threshold=0.25)
    assert predictor.high_threshold == 0.30
    assert predictor.medium_threshold == 0.25
    
    dummy_input = {
        "age": 35,
        "gender": "Female",
        "lead_time_days": 10.0,
        "day_of_week": 2,
        "hour_of_day": 10,
        "is_weekend": False,
        "is_afternoon": False,
        "prior_appointments": 2,
        "prior_no_shows": 0,
        "prior_cancellations": 0,
        "prior_no_show_rate": 0.0,
        "existing_diagnoses_count": 0,
        "chronic_condition_count": 0,
        "department_name": "General Medicine",
    }
    
    result = predictor.predict_risk(dummy_input)
    assert result["risk_tier"] in ("LOW", "MEDIUM", "HIGH")
    assert "no_show_percentage" in result

