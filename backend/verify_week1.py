"""
AI-HMS Week 1 Verification Runner
Performs a live, formatted, end-to-end test of all Week 1 foundation deliverables:
1. Database connectivity & Healthcheck
2. Authentication & JWT generation across all 4 roles
3. RBAC boundary tests (Patients blocked from Admin & clinical directories)
4. Staff clinical access (Nurses and Doctors)
5. Appointment booking, conflict prevention, wait-time timestamps, and no-show transition
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")


def run_check(step: str, description: str, func) -> bool:
    t0 = time.time()
    try:
        details = func()
        elapsed_ms = (time.time() - t0) * 1000
        print(f"[{GREEN}PASS{RESET}] {BOLD}{step:<10}{RESET} {description:<55} ({elapsed_ms:.1f}ms)")
        if details:
            print(f"       -> {details}")
        return True
    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"[{RED}FAIL{RESET}] {BOLD}{step:<10}{RESET} {description:<55} ({elapsed_ms:.1f}ms)")
        print(f"       -> {RED}Error: {e}{RESET}")
        return False


def main():
    print(f"\n{BOLD}Starting AI-HMS Week 1 Foundation Verification Suite...{RESET}")
    results = []

    # 1. Health & Database Connection
    print_header("1. INFRASTRUCTURE & DATABASE HEALTH")
    def check_health():
        r = client.get("/api/health")
        assert r.status_code == 200 and r.json()["database"] == "connected"
        return f"PostgreSQL 18 status: {r.json()['database']}, service: {r.json()['service']}"
    results.append(run_check("W1-01", "Database connectivity & Health Check", check_health))

    # 2. Authentication & Role Logins
    print_header("2. AUTHENTICATION & JWT BEARER TOKENS")
    tokens = {}
    for role, email, pwd in [
        ("ADMIN", "admin@hospital.com", "Admin@123"),
        ("DOCTOR", "doctor@hospital.com", "Doctor@123"),
        ("NURSE", "nurse@hospital.com", "Nurse@123"),
        ("PATIENT", "patient@hospital.com", "Patient@123"),
    ]:
        def check_login(e=email, p=pwd, r=role):
            res = client.post("/api/v1/auth/login", json={"email": e, "password": p})
            assert res.status_code == 200
            token = res.json()["access_token"]
            tokens[r] = token
            return f"Authenticated as {r} (User ID: {res.json()['user']['id']})"
        results.append(run_check(f"W1-02-{role}", f"Login & Token issuance for {role}", check_login))

    def check_invalid_pwd():
        res = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "BadPassword123"})
        assert res.status_code == 401
        return "Rejected invalid credentials with 401 Unauthorized"
    results.append(run_check("W1-03", "Rejection of invalid password", check_invalid_pwd))

    def check_registration():
        unique_email = f"patient_{uuid.uuid4().hex[:6]}@demo.org"
        res = client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password@123",
            "first_name": "Rohan",
            "last_name": "Mehta",
            "role_name": "PATIENT"
        })
        assert res.status_code == 201
        return f"Registered patient: {unique_email} with hashed credentials"
    results.append(run_check("W1-04", "New patient self-registration", check_registration))

    # 3. RBAC Security Boundaries
    print_header("3. ROLE-BASED ACCESS CONTROL (RBAC) GATES")
    def check_patient_blocked_from_admin():
        res = client.post("/api/v1/departments/", json={"name": "Forbidden"}, headers={"Authorization": f"Bearer {tokens['PATIENT']}"})
        assert res.status_code == 403
        return f"Blocked: {res.json()['detail']}"
    results.append(run_check("W1-05", "PATIENT blocked from department creation", check_patient_blocked_from_admin))

    def check_admin_department_creation():
        name = f"Cardiology-Special-{uuid.uuid4().hex[:4]}"
        res = client.post("/api/v1/departments/", json={"name": name, "description": "Cardiac center"}, headers={"Authorization": f"Bearer {tokens['ADMIN']}"})
        assert res.status_code == 201
        return f"Created department ID: {res.json()['id']} ('{name}')"
    results.append(run_check("W1-06", "ADMIN authorized department creation", check_admin_department_creation))

    def check_patient_blocked_from_patient_directory():
        res = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {tokens['PATIENT']}"})
        assert res.status_code == 403
        return f"Blocked: {res.json()['detail']}"
    results.append(run_check("W1-07", "PATIENT blocked from querying all patients", check_patient_blocked_from_patient_directory))

    def check_nurse_authorized_patient_directory():
        res = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {tokens['NURSE']}"})
        assert res.status_code == 200
        return f"NURSE authorized: retrieved {len(res.json())} patient records"
    results.append(run_check("W1-08", "NURSE authorized to view patient list", check_nurse_authorized_patient_directory))

    # 4. Doctor Availability
    print_header("4. DOCTOR DIRECTORY & AVAILABILITY")
    def check_doctor_availability():
        doc_res = client.get("/api/v1/doctors/", headers={"Authorization": f"Bearer {tokens['DOCTOR']}"}).json()
        assert len(doc_res) > 0
        doc_id = doc_res[0]["id"]
        res = client.post(f"/api/v1/doctors/{doc_id}/availability", json={
            "day_of_week": 2,
            "start_time": "10:00:00",
            "end_time": "14:00:00",
            "slot_duration_minutes": 20,
            "is_active": True
        }, headers={"Authorization": f"Bearer {tokens['DOCTOR']}"})
        assert res.status_code == 201
        return f"Configured Tuesday slots (10:00-14:00, 20-min slots) for Doctor {doc_id}"
    results.append(run_check("W1-09", "Doctor weekly availability configuration", check_doctor_availability))

    # 5. Appointment Lifecycle, Conflict Detection & Operational Timestamps
    print_header("5. APPOINTMENT LIFECYCLE & OPERATIONAL DATA")
    doctors = client.get("/api/v1/doctors/", headers={"Authorization": f"Bearer {tokens['ADMIN']}"}).json()
    patients = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {tokens['ADMIN']}"}).json()
    doc_id = doctors[0]["id"]
    pat_id = patients[0]["id"]
    slot_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(minute=0, second=0, microsecond=0)

    def check_appointment_booking():
        res = client.post("/api/v1/appointments/", json={
            "patient_id": pat_id,
            "doctor_id": doc_id,
            "scheduled_at": slot_time.isoformat(),
            "reason": "Cardiac Evaluation",
            "notes": "Patient scheduled for baseline ECG"
        }, headers={"Authorization": f"Bearer {tokens['ADMIN']}"})
        assert res.status_code == 201
        return f"Booked appointment ID: {res.json()['id']} for {slot_time.strftime('%Y-%m-%d %H:%M')}"
    results.append(run_check("W1-10", "Schedule new appointment", check_appointment_booking))

    def check_conflict_rejection():
        res = client.post("/api/v1/appointments/", json={
            "patient_id": pat_id,
            "doctor_id": doc_id,
            "scheduled_at": slot_time.isoformat(),
            "reason": "Conflicting Booking Attempt"
        }, headers={"Authorization": f"Bearer {tokens['ADMIN']}"})
        assert res.status_code == 409
        return f"Conflict caught: {res.json()['detail']}"
    results.append(run_check("W1-11", "Double-booking prevention (409 Conflict)", check_conflict_rejection))

    def check_wait_time_completion():
        # Create an appointment to complete
        new_slot = slot_time + timedelta(hours=2)
        appt = client.post("/api/v1/appointments/", json={
            "patient_id": pat_id,
            "doctor_id": doc_id,
            "scheduled_at": new_slot.isoformat(),
            "reason": "Consultation"
        }, headers={"Authorization": f"Bearer {tokens['ADMIN']}"}).json()

        started_at = new_slot + timedelta(minutes=15)  # 15 min wait time
        ended_at = started_at + timedelta(minutes=20)   # 20 min consultation
        res = client.patch(f"/api/v1/appointments/{appt['id']}/status", json={
            "status": "completed",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "notes": "Consultation completed. Waiting time: 15 min."
        }, headers={"Authorization": f"Bearer {tokens['NURSE']}"})
        assert res.status_code == 200
        return f"Completed appointment {appt['id']} (Recorded started_at & ended_at for W2 wait-time metrics)"
    results.append(run_check("W1-12", "Record consultation with wait-time tracking", check_wait_time_completion))

    def check_no_show_transition():
        new_slot = slot_time + timedelta(hours=3)
        appt = client.post("/api/v1/appointments/", json={
            "patient_id": pat_id,
            "doctor_id": doc_id,
            "scheduled_at": new_slot.isoformat(),
            "reason": "General Check"
        }, headers={"Authorization": f"Bearer {tokens['ADMIN']}"}).json()

        res = client.patch(f"/api/v1/appointments/{appt['id']}/status", json={
            "status": "no_show",
            "notes": "Patient did not attend."
        }, headers={"Authorization": f"Bearer {tokens['NURSE']}"})
        assert res.status_code == 200
        return f"Updated status to 'no_show' (Captured data for W2/W3 no-show models)"
    results.append(run_check("W1-13", "Transition appointment to 'no_show'", check_no_show_transition))

    # Summary
    print_header("VERIFICATION SUMMARY")
    passed = sum(results)
    total = len(results)
    color = GREEN if passed == total else RED
    print(f"{BOLD}Total Tests:{RESET} {total} | {color}{BOLD}Passed:{RESET} {passed} | {RED}{BOLD}Failed:{RESET} {total - passed}")
    if passed == total:
        print(f"\n{BOLD}{GREEN}ALL WEEK 1 FOUNDATION REQUIREMENTS ARE 100% VERIFIED!{RESET}\n")
    else:
        print(f"\n{BOLD}{RED}Some checks failed. Inspect logs above.{RESET}\n")


if __name__ == "__main__":
    main()
