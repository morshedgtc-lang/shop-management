from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    default_price: float = Field(0, ge=0)
    wholesale_price: float = Field(0, ge=0)
    currency: str = "USD"
    active: bool = True


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    default_price: Optional[float] = Field(None, ge=0)
    wholesale_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    active: Optional[bool] = None


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: str
    default_price: float
    wholesale_price: float = 0
    currency: str
    active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
