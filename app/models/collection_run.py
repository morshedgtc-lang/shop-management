from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class CollectionRun(Base):
    __tablename__ = "collection_runs"
    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("intermediate_shops.id"), nullable=False)
    collected_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_collected = Column(Float, default=0)
    notes = Column(String, default="")
    collected_at = Column(DateTime, server_default=func.now())
    shop = relationship("IntermediateShop")
    collector = relationship("User", foreign_keys=[collected_by])
