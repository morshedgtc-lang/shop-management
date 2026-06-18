from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ServiceCreate(BaseModel):
    name: str
    description: str = ""
    default_price: float = 0
    currency: str = "USD"


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_price: Optional[float] = None
    currency: Optional[str] = None
    active: Optional[bool] = None


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: str
    default_price: float
    currency: str
    active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
