import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.utils.auth import hash_password, require_admin

router = APIRouter(prefix="/api/staff", tags=["staff"])


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class StaffCreateRequest:
    def __init__(
        self,
        name: str,
        email: str,
        phone: str = "",
        role: str = "staff",
    ):
        self.name = name
        self.email = email
        self.phone = phone
        self.role = role


class StaffUpdateRequest:
    def __init__(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[str] = None,
        active: Optional[bool] = None,
    ):
        self.name = name
        self.email = email
        self.phone = phone
        self.role = role
        self.active = active


@router.get("/", response_model=list[UserResponse])
def list_staff(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(User)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term))
            | (User.email.ilike(search_term))
            | (User.phone.ilike(search_term))
        )
    staff = query.offset((page - 1) * limit).limit(limit).all()
    return staff


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_staff(
    name: str = Query(...),
    email: str = Query(...),
    phone: str = Query(""),
    role: str = Query("staff"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    if role not in ["admin", "manager", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be admin, manager, or staff",
        )
    plain_password = generate_password()
    user = User(
        name=name,
        email=email,
        phone=phone,
        role=role,
        password_hash=hash_password(plain_password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user": UserResponse.model_validate(user),
        "password": plain_password,
        "message": "Staff created successfully. Save this password - it will not be shown again.",
    }


@router.put("/{user_id}", response_model=UserResponse)
def update_staff(
    user_id: int,
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
        )
    if email and email != user.email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        user.email = email
    if name is not None:
        user.name = name
    if phone is not None:
        user.phone = phone
    if role is not None:
        if role not in ["admin", "manager", "staff"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role",
            )
        user.role = role
    if active is not None:
        user.active = active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_staff(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    user.active = False
    db.commit()
