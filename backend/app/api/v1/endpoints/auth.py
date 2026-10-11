from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, require_admin
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.auth import Role, User
from app.schemas.auth import LoginRequest, StaffUserCreate, Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate user with email and password. Returns JWT bearer access token.
    """
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == request.email.lower().strip())
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    role_name = user.role.name if user.role else "PATIENT"
    token = create_access_token(subject=str(user.id), role=role_name)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current logged in user details with active role.
    """
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    request: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Public registration endpoint. Restricted strictly to PATIENT role to prevent privilege escalation.
    """
    # Enforce PATIENT role for public unauthenticated registrations
    requested_role = (request.role_name or "PATIENT").upper().strip()
    if requested_role != "PATIENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is restricted to PATIENT role. Staff creation requires an Administrator.",
        )

    email_clean = request.email.lower().strip()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    role = db.query(Role).filter(Role.name == "PATIENT").first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default PATIENT role not configured in database",
        )

    new_user = User(
        email=email_clean,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role_id=role.id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    request: StaffUserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> Any:
    """
    Create a hospital staff user (ADMIN, DOCTOR, NURSE). Requires ADMIN authorization.
    """
    role_clean = request.role_name.upper().strip()
    role = db.query(Role).filter(Role.name == role_clean).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid staff role: {request.role_name}",
        )

    email_clean = request.email.lower().strip()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    new_staff = User(
        email=email_clean,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role_id=role.id,
        is_active=True,
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff
