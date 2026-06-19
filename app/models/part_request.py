from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class PartRequest(Base):
    __tablename__ = "part_requests"
    id = Column(Integer, primary_key=True, index=True)
    repair_id = Column(Integer, ForeignKey("repairs.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    fulfilled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    quantity = Column(Integer, default=1)
    status = Column(String, default="PENDING")
    notes = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    repair = relationship("Repair", backref="part_requests")
    part = relationship("Part")
    requester = relationship("User", foreign_keys=[requested_by])
    fulfiller = relationship("User", foreign_keys=[fulfilled_by])
