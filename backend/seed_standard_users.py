import uuid
from datetime import date
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.auth import Role, User
from app.models.clinical import Patient
from app.models.hospital import Department, Doctor


def seed_standard_users():
    db: Session = SessionLocal()
    try:
        # Fetch roles
        roles = {r.name.upper(): r for r in db.query(Role).all()}
        print(f"Available roles: {list(roles.keys())}")

        # Ensure Cardiology department
        dept = db.query(Department).filter(Department.name == "Cardiology").first()
        if not dept:
            dept = Department(name="Cardiology", description="Cardiology & Cardiovascular Sciences")
            db.add(dept)
            db.flush()

        users_to_seed = [
            ("admin@hospital.com", "Admin@123", "ADMIN", "Super", "Admin"),
            ("doctor@hospital.com", "Doctor@123", "DOCTOR", "Rahul", "Sharma"),
            ("nurse@hospital.com", "Nurse@123", "NURSE", "Ananya", "Sen"),
            ("patient@hospital.com", "Patient@123", "PATIENT", "Sunita", "Verma"),
            ("patient2@hospital.com", "Patient@123", "PATIENT", "Amit", "Kumar"),
        ]

        for email, pwd, role_name, fname, lname in users_to_seed:
            user = db.query(User).filter(User.email == email).first()
            role_obj = roles.get(role_name)
            if not role_obj:
                print(f"Skipping {email}: Role {role_name} not found")
                continue

            if not user:
                user = User(
                    email=email,
                    password_hash=get_password_hash(pwd),
                    first_name=fname,
                    last_name=lname,
                    role_id=role_obj.id,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                print(f"Created user {email} ({role_name})")
            else:
                user.password_hash = get_password_hash(pwd)
                user.role_id = role_obj.id
                db.flush()
                print(f"Updated user credentials for {email} ({role_name})")

            # Doctor profile check
            if role_name == "DOCTOR":
                doc = db.query(Doctor).filter(Doctor.user_id == user.id).first()
                if not doc:
                    doc = Doctor(
                        user_id=user.id,
                        department_id=dept.id,
                        license_number=f"DOC-LIC-{uuid.uuid4().hex[:6].upper()}",
                        specialization="Cardiologist",
                    )
                    db.add(doc)
                    db.flush()
                    print(f"Created doctor profile for {email}")

            # Patient profile check
            if role_name == "PATIENT":
                pat = db.query(Patient).filter(Patient.user_id == user.id).first()
                if not pat:
                    pat = Patient(
                        user_id=user.id,
                        date_of_birth=date(1985, 6, 15),
                        gender="Female",
                        blood_group="B+",
                        phone="+91-9876543210",
                        address="12 Park Street, Kolkata",
                    )
                    db.add(pat)
                    db.flush()
                    print(f"Created patient profile for {email}")

        db.commit()
        print("Standard users seeded successfully!")
    except Exception as ex:
        db.rollback()
        print(f"Error seeding standard users: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_standard_users()
