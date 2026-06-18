from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    default_price = Column(Float, default=0)
    currency = Column(String, default="USD")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
