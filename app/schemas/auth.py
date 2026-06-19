from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.database import ROLE_ADMIN, ROLE_TECHNICIAN, ROLE_WAREHOUSE, ROLE_RECEPTION


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: str
    active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
