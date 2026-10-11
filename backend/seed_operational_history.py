"""
Operational History Seeder for AI-HMS
Generates a statistically realistic operational appointment cohort across 90 days.
Establishes rich distributions for:
- Waiting times (5 to 45 mins with afternoon peak delays)
- Appointment durations (10 to 40 mins)
- Cancellation rate (~8-10%)
- No-show rate (~18-22% hospital baseline)
- Capacity utilization by doctor and department
"""

import random
import uuid
from datetime import date, datetime, timedelta, time, timezone
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.auth import Role, User
from app.models.clinical import Patient
from app.models.hospital import Department, Doctor, DoctorAvailability, Appointment

# Deterministic random seed for reproducible benchmark baselines
random.seed(42)


def seed_additional_doctors(db: Session, roles: dict, departments: dict):
    new_doctors_spec = [
        ("dr.amit.verma@hospital.com", "Amit", "Verma", "General Medicine", "Internal Medicine", "LIC-GM-10928"),
        ("dr.sunita.rao@hospital.com", "Sunita", "Rao", "Orthopedics", "Orthopedic Surgeon", "LIC-ORT-48211"),
        ("dr.vikram.sen@hospital.com", "Vikram", "Sen", "Pediatrics-893207", "Pediatrician", "LIC-PED-77341"),
    ]

    doctor_ids = []
    for email, fname, lname, dept_name, spec, lic in new_doctors_spec:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                password_hash=get_password_hash("Doctor@123"),
                first_name=fname,
                last_name=lname,
                role_id=roles["DOCTOR"].id,
                is_active=True,
            )
            db.add(user)
            db.flush()

        doc = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        dept = db.query(Department).filter(Department.name == dept_name).first()
        dept_id = dept.id if dept else None

        if not doc:
            doc = Doctor(
                user_id=user.id,
                department_id=dept_id,
                license_number=lic,
                specialization=spec,
            )
            db.add(doc)
            db.flush()

        doctor_ids.append(doc.id)

    # Add standard availability for all doctors
    all_doctors = db.query(Doctor).all()
    for doc in all_doctors:
        existing_avail = db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doc.id).first()
        if not existing_avail:
            for day in range(1, 6):  # Mon-Fri
                db.add(DoctorAvailability(
                    doctor_id=doc.id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    slot_duration_minutes=20,
                    is_active=True,
                ))
    db.flush()


def generate_operational_appointments(db: Session):
    doctors = db.query(Doctor).all()
    patients = db.query(Patient).all()
    
    if not doctors or not patients:
        print("Missing doctors or patients to generate appointments.")
        return

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=75)
    
    existing_count = db.query(Appointment).count()
    print(f"Current appointment count: {existing_count}")
    if existing_count >= 500:
        print("Sufficient operational appointments already exist.")
        return

    appointments_to_add = []
    reasons = [
        "Hypertension Routine Follow-up",
        "Chest Discomfort & Palpitations",
        "Migraine & Chronic Headache",
        "Knee Joint Stiffness & Pain",
        "Seasonal Bronchitis & Cough",
        "Post-operative Review",
        "Type 2 Diabetes Monitoring",
        "Annual Preventive Checkup",
        "Lower Back Pain Consultation",
        "Childhood Immunization & Growth Check",
    ]

    cancellation_reasons = [
        "Patient experienced transport disruption",
        "Rescheduled to later date due to work",
        "Symptoms resolved prior to appointment",
        "Conflict with family emergency",
        "Admitted to inpatient facility elsewhere",
    ]

    # Generate appointments over 75 days in the past and 10 days in the future
    current_day = start_date
    slot_hours = [9, 10, 11, 12, 14, 15, 16]

    while current_day <= now + timedelta(days=10):
        # Skip Sundays
        if current_day.weekday() != 6:
            for doc in doctors:
                # 3 to 6 appointments per doctor per working day
                daily_slots = random.sample(slot_hours, k=random.randint(3, 5))
                for hour in daily_slots:
                    patient = random.choice(patients)
                    scheduled_time = current_day.replace(hour=hour, minute=random.choice([0, 20, 40]), second=0, microsecond=0)

                    # Determine status
                    if scheduled_time > now:
                        status = "scheduled"
                        started_at = None
                        ended_at = None
                        notes = "Scheduled appointment"
                    else:
                        rand_roll = random.random()
                        if rand_roll < 0.69:  # 69% Completed
                            status = "completed"
                            # Waiting time: Afternoon hours experience higher backlog
                            base_wait = 14 if hour < 13 else 24
                            wait_mins = max(2.0, min(58.0, random.gauss(base_wait, 7.5)))
                            duration_mins = max(10.0, min(45.0, random.gauss(20, 5)))

                            started_at = scheduled_time + timedelta(minutes=wait_mins)
                            ended_at = started_at + timedelta(minutes=duration_mins)
                            notes = f"Consultation conducted. Wait time: {int(wait_mins)} min."
                        elif rand_roll < 0.89:  # 20% No-show
                            status = "no_show"
                            started_at = None
                            ended_at = None
                            notes = "Patient did not attend appointment without notice."
                        else:  # 11% Cancelled
                            status = "cancelled"
                            started_at = None
                            ended_at = None
                            notes = random.choice(cancellation_reasons)

                    booking_lead_days = random.randint(1, 28)
                    booking_lead_hours = random.randint(1, 12)
                    created_time = scheduled_time - timedelta(days=booking_lead_days, hours=booking_lead_hours)

                    appt = Appointment(
                        patient_id=patient.id,
                        doctor_id=doc.id,
                        scheduled_at=scheduled_time,
                        status=status,
                        reason=random.choice(reasons),
                        notes=notes,
                        started_at=started_at,
                        ended_at=ended_at,
                        created_at=created_time,
                    )
                    appointments_to_add.append(appt)

        current_day += timedelta(days=1)

    db.bulk_save_objects(appointments_to_add)
    db.commit()
    total_count = db.query(Appointment).count()
    print(f"Generated {len(appointments_to_add)} operational records. Total appointments now: {total_count}")


def main():
    db = SessionLocal()
    try:
        roles = {r.name.upper(): r for r in db.query(Role).all()}
        departments = {d.name: d for d in db.query(Department).all()}
        seed_additional_doctors(db, roles, departments)
        generate_operational_appointments(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
