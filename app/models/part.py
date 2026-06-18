from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base


class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    model = Column(String, default="")
    stock_qty = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    currency = Column(String, default="USD")
    min_stock_alert = Column(Integer, default=5)
    created_at = Column(DateTime, server_default=func.now())
