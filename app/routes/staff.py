import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.staff import StaffCreate, StaffUpdate
from app.utils.auth import hash_password
from app.utils.permissions import require_admin

router = APIRouter(prefix="/api/staff", tags=["staff"])


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("", response_model=list[UserResponse])
async def list_staff(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    query = select(User)
    if search:
        term = f"%{search}%"
        query = query.where(
            (User.name.ilike(term)) | (User.email.ilike(term)) | (User.phone.ilike(term))
        )
    rows = (
        (await db.execute(query.offset((page - 1) * limit).limit(limit)))
        .scalars()
        .all()
    )
    return rows


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")
    plain_password = generate_password()
    user = User(
        name=data.name, email=data.email, phone=data.phone, role=data.role,
        password_hash=hash_password(plain_password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "user": UserResponse.model_validate(user),
        "password": plain_password,
        "message": "Staff created successfully. Save this password - it will not be shown again.",
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_staff(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_staff(
    user_id: int,
    data: StaffUpdate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    if data.email and data.email != user.email:
        existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        user.email = data.email
    if data.name is not None:
        user.name = data.name
    if data.phone is not None:
        user.phone = data.phone
    if data.role is not None:
        user.role = data.role
    if data.active is not None:
        user.active = data.active
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=dict)
async def reset_staff_password(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reset your own password. Use Settings page.")
    plain_password = generate_password()
    user.password_hash = hash_password(plain_password)
    await db.commit()
    await db.refresh(user)
    return {
        "password": plain_password,
        "message": "Password reset successfully. Save this password - it will not be shown again.",
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_staff(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")
    user.active = False
    await db.commit()
