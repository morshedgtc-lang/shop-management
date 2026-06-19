from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{7,20}$')
    email: str = ""
    address: str = ""


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{7,20}$')
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    address: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
