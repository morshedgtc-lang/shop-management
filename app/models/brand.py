from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
