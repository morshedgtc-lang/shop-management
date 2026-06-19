from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from app.database import VALID_ROLES


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str
    phone: str = ""
    role: str = "retailer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if "@" not in v:
                raise ValueError("Invalid email format")
            return v.lower().strip()
        return v
