from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ==============================================================================
# 1. Health & Infrastructure
# ==============================================================================
def test_01_health_check():
    """Verify backend health and live database connection."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


# ==============================================================================
# 2. Authentication & User Lifecycle
# ==============================================================================
def test_02_login_all_roles():
    """Verify login and JWT token issuance for all 4 standard roles."""
    roles = [
        ("admin@hospital.com", "Admin@123", "ADMIN"),
        ("doctor@hospital.com", "Doctor@123", "DOCTOR"),
        ("nurse@hospital.com", "Nurse@123", "NURSE"),
        ("patient@hospital.com", "Patient@123", "PATIENT"),
    ]
    for email, pwd, expected_role in roles:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"]["name"] == expected_role


def test_03_login_invalid_password():
    """Verify rejection of incorrect passwords."""
    resp = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "WrongPassword!999"})
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


def test_04_login_nonexistent_user():
    """Verify rejection of non-existent emails."""
    resp = client.post("/api/v1/auth/login", json={"email": "ghost@hospital.com", "password": "Password123"})
    assert resp.status_code == 401


def test_05_register_new_patient_and_login():
    """Verify user registration defaults to PATIENT role and can log in."""
    unique_email = f"test.patient.{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword@123",
            "first_name": "Test",
            "last_name": "User",
            "role_name": "PATIENT",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["email"] == unique_email
    assert reg_data["role"]["name"] == "PATIENT"

    # Verify duplicate registration is rejected
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword@123",
            "first_name": "Duplicate",
            "role_name": "PATIENT",
        },
    )
    assert dup_resp.status_code == 400

    # Verify the new user can log in
    login_resp = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "SecurePassword@123"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_06_unauthenticated_request_rejected():
    """Verify endpoints reject requests missing Bearer tokens."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_07_tampered_token_rejected():
    """Verify endpoints reject forged/tampered JWT tokens."""
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"})
    assert resp.status_code == 401


# ==============================================================================
# 3. RBAC Matrix & Boundaries
# ==============================================================================
def test_08_rbac_patient_cannot_create_department():
    """Ensure PATIENT role cannot create hospital departments (403 Forbidden)."""
    pat_token = client.post("/api/v1/auth/login", json={"email": "patient@hospital.com", "password": "Patient@123"}).json()["access_token"]
    resp = client.post(
        "/api/v1/departments/",
        json={"name": "Forbidden Dept", "description": "Should fail"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert resp.status_code == 403


def test_09_rbac_admin_can_create_and_update_department():
    """Ensure ADMIN role can create and update hospital departments."""
    adm_token = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"}).json()["access_token"]
    dept_name = f"Pediatrics-{uuid.uuid4().hex[:6]}"
    
    # Create
    create_resp = client.post(
        "/api/v1/departments/",
        json={"name": dept_name, "description": "Child Healthcare"},
        headers={"Authorization": f"Bearer {adm_token}"},
    )
    assert create_resp.status_code == 201
    dept_id = create_resp.json()["id"]

    # Update
    update_resp = client.put(
        f"/api/v1/departments/{dept_id}",
        json={"description": "Comprehensive Pediatric Care"},
        headers={"Authorization": f"Bearer {adm_token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Comprehensive Pediatric Care"


def test_10_rbac_patient_cannot_list_all_patients():
    """Ensure PATIENT cannot query the complete patient directory."""
    pat_token = client.post("/api/v1/auth/login", json={"email": "patient@hospital.com", "password": "Patient@123"}).json()["access_token"]
    resp = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp.status_code == 403


def test_11_rbac_nurse_and_doctor_can_list_patients():
    """Ensure clinical staff (DOCTOR and NURSE) can access the patient directory."""
    doc_token = client.post("/api/v1/auth/login", json={"email": "doctor@hospital.com", "password": "Doctor@123"}).json()["access_token"]
    nurse_token = client.post("/api/v1/auth/login", json={"email": "nurse@hospital.com", "password": "Nurse@123"}).json()["access_token"]

    doc_resp = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {doc_token}"})
    assert doc_resp.status_code == 200
    assert isinstance(doc_resp.json(), list)

    nurse_resp = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {nurse_token}"})
    assert nurse_resp.status_code == 200
    assert isinstance(nurse_resp.json(), list)


# ==============================================================================
# 4. Doctor Scheduling & Availability
# ==============================================================================
def test_12_doctor_availability_configuration():
    """Verify doctors can configure their own weekly availability schedules."""
    doc_token = client.post("/api/v1/auth/login", json={"email": "doctor@hospital.com", "password": "Doctor@123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {doc_token}"}

    # Retrieve doctor profile
    doc_info = client.get("/api/v1/auth/me", headers=headers).json()
    doctors = client.get("/api/v1/doctors/", headers=headers).json()
    doc_rec = next((d for d in doctors if d["user_id"] == doc_info["id"]), None)
    assert doc_rec is not None
    doctor_id = doc_rec["id"]

    # Configure Monday availability 09:00 - 13:00
    avail_resp = client.post(
        f"/api/v1/doctors/{doctor_id}/availability",
        json={
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "13:00:00",
            "slot_duration_minutes": 20,
            "is_active": True,
        },
        headers=headers,
    )
    assert avail_resp.status_code == 201
    assert avail_resp.json()["day_of_week"] == 1
    assert avail_resp.json()["slot_duration_minutes"] == 20


# ==============================================================================
# 5. Appointment Lifecycle, Conflicts & Status Tracking
# ==============================================================================
def test_13_appointment_double_booking_conflict():
    """Verify schedule conflict detection: double booking the same doctor slot returns 409 Conflict."""
    adm_token = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {adm_token}"}

    import random
    doctors = client.get("/api/v1/doctors/", headers=headers).json()
    doctor_id = doctors[0]["id"]
    patients = client.get("/api/v1/patients/", headers=headers).json()
    patient_id = patients[0]["id"]

    # Use a random future date offset to prevent collisions with previous test executions
    rand_offset_days = random.randint(40, 120)
    conflict_time = (datetime.now(timezone.utc) + timedelta(days=rand_offset_days, seconds=random.randint(1, 500))).replace(microsecond=0).isoformat()

    # First booking succeeds
    resp1 = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": conflict_time,
            "reason": "Cardiology Consultation 1",
        },
        headers=headers,
    )
    assert resp1.status_code == 201

    # Second booking at identical time slot fails with 409 Conflict
    resp2 = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": conflict_time,
            "reason": "Conflicting Consultation",
        },
        headers=headers,
    )
    assert resp2.status_code == 409
    assert "already has an active appointment" in resp2.json()["detail"]


def test_14_appointment_lifecycle_completed_and_wait_time():
    """Verify transition to 'completed' with accurate start and end timestamps."""
    nurse_token = client.post("/api/v1/auth/login", json={"email": "nurse@hospital.com", "password": "Nurse@123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {nurse_token}"}

    doctors = client.get("/api/v1/doctors/", headers=headers).json()
    patients = client.get("/api/v1/patients/", headers=headers).json()
    
    scheduled_time = datetime.now(timezone.utc) + timedelta(days=3)
    booking = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": patients[0]["id"],
            "doctor_id": doctors[0]["id"],
            "scheduled_at": scheduled_time.isoformat(),
            "reason": "Blood Pressure Follow-up",
        },
        headers=headers,
    ).json()

    appt_id = booking["id"]
    started_time = scheduled_time + timedelta(minutes=12)  # 12 min wait
    ended_time = started_time + timedelta(minutes=25)      # 25 min duration

    status_resp = client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={
            "status": "completed",
            "started_at": started_time.isoformat(),
            "ended_at": ended_time.isoformat(),
            "notes": "Consultation concluded successfully.",
        },
        headers=headers,
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "completed"
    assert data["started_at"] is not None
    assert data["ended_at"] is not None


def test_15_appointment_no_show_transition():
    """Verify transition to 'no_show' status to build historical baseline for ML."""
    nurse_token = client.post("/api/v1/auth/login", json={"email": "nurse@hospital.com", "password": "Nurse@123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {nurse_token}"}

    doctors = client.get("/api/v1/doctors/", headers=headers).json()
    patients = client.get("/api/v1/patients/", headers=headers).json()

    booking = client.post(
        "/api/v1/appointments/",
        json={
            "patient_id": patients[0]["id"],
            "doctor_id": doctors[0]["id"],
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "reason": "Diabetes Routine Check",
        },
        headers=headers,
    ).json()

    appt_id = booking["id"]

    status_resp = client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={
            "status": "no_show",
            "notes": "Patient did not show up or notify hospital.",
        },
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "no_show"
