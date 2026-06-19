from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class CollectionItem(Base):
    __tablename__ = "collection_items"
    id = Column(Integer, primary_key=True, index=True)
    collection_run_id = Column(Integer, ForeignKey("collection_runs.id"), nullable=False)
    repair_id = Column(Integer, ForeignKey("repairs.id"), nullable=False)
    amount_paid = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())
    collection_run = relationship("CollectionRun", backref="items")
    repair = relationship("Repair")
