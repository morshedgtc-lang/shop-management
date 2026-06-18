from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(String, default="draft")
    payment_type = Column(String, default="credit")
    notes = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    supplier = relationship("Supplier", backref="purchase_orders")
    creator = relationship("User", foreign_keys=[created_by])
    items = relationship("PurchaseOrderItem", backref="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    sku = Column(String, default="")
    qty_ordered = Column(Integer, default=1)
    qty_received = Column(Integer, default=0)
    cost_price = Column(Float, default=0)
    invoice_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    part_status = Column(String, default="pending")

    part = relationship("Part")


class PurchaseOrderReceipt(Base):
    __tablename__ = "purchase_order_receipts"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    invoice_number = Column(String, default="")
    invoice_date = Column(String, default="")
    notes = Column(Text, default="")
    received_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    purchase_order = relationship("PurchaseOrder", backref="receipts")
    receiver = relationship("User", foreign_keys=[received_by])
    receipt_items = relationship("PurchaseOrderReceiptItem", backref="receipt", cascade="all, delete-orphan")


class PurchaseOrderReceiptItem(Base):
    __tablename__ = "purchase_order_receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("purchase_order_receipts.id"), nullable=False)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)
    qty_received = Column(Integer, default=0)
    cost_price = Column(Float, default=0)

    po_item = relationship("PurchaseOrderItem")


class PurchaseOrderDiscrepancy(Base):
    __tablename__ = "purchase_order_discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)
    field = Column(String, nullable=False)
    expected = Column(Float, default=0)
    actual = Column(Float, default=0)
    note = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    po_item = relationship("PurchaseOrderItem")
