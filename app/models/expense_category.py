from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    icon = Column(String, default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
