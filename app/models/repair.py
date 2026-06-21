from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base

class Repair(Base):
    __tablename__ = "repairs"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="PENDING_ESTIMATE")
    model = Column(String, nullable=False)
    brand = Column(String, default="")
    passcode = Column(String, default="")
    issues = Column(Text, nullable=False)
    imei = Column(String, default="")
    estimated_cost = Column(Float, default=0)
    estimated_time = Column(String, default="")
    actual_cost = Column(Float, default=0)
    service_fee = Column(Float, default=0)
    payment_status = Column(String, default="UNPAID")
    order_type = Column(String, default="OR")
    intermediate_shop_id = Column(Integer, ForeignKey("intermediate_shops.id"), nullable=True)
    notes = Column(Text, default="")
    handover_items = Column(Text, default="[]")
    handover_memory_note = Column(String, default="")
    condition_data = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    customer = relationship("Customer", backref="repairs")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])
    intermediate_shop = relationship("IntermediateShop", backref="repairs")
