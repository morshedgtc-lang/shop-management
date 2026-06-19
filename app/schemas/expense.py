from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    amount: float = Field(..., ge=0)
    category_id: int
    currency: str = "USD"
    note: str = ""
    date: Optional[str] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, ge=0)
    category_id: Optional[int] = None
    currency: Optional[str] = None
    note: Optional[str] = None
    date: Optional[str] = None


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = ""


class ExpenseCategoryResponse(BaseModel):
    id: int
    name: str
    icon: str
    active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseResponse(BaseModel):
    id: int
    date: str
    amount: float
    currency: str
    category_id: int
    category_name: str = ""
    note: str
    created_by: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
