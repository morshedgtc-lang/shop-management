from sqlalchemy import Column, Integer, String
from app.database import Base


class PartCategory(Base):
    __tablename__ = "part_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    sort_order = Column(Integer, default=0)
