from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ExpenseCreate(BaseModel):
    amount: float
    category_id: int
    currency: str = "USD"
    note: str = ""
    date: Optional[str] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category_id: Optional[int] = None
    currency: Optional[str] = None
    note: Optional[str] = None
    date: Optional[str] = None


class ExpenseCategoryCreate(BaseModel):
    name: str
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
