from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class PartType(Base):
    __tablename__ = "part_types"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("part_categories.id"), nullable=False)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    category = relationship("PartCategory", backref="part_types")
