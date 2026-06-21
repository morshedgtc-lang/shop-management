from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class DailySaleCreate(BaseModel):
    amount: float = Field(..., ge=0)
    currency: str = "USD"
    category: str = "general"
    note: str = ""
    date: Optional[str] = None


class DailySaleUpdate(BaseModel):
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None
    date: Optional[str] = None


class DailySaleResponse(BaseModel):
    id: int
    date: str
    amount: float
    currency: str
    category: str
    note: str
    created_by: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
