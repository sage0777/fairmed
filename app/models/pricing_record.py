import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class PricingRecord(Base):
    __tablename__ = "pricing_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medicine_id = Column(String(36), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, index=True)
    pricing_category = Column(String(100), nullable=False, index=True)  # DPCO_SCHEDULED_CEILING, TRADE_MARGIN_CAPPED, NOTIFIED_MRP, NON_SCHEDULED
    price_type = Column(String(50), default="CEILING_PRICE", nullable=False)  # CEILING_PRICE, NOTIFIED_MRP, RETAIL_PRICE
    ceiling_price = Column(Numeric(12, 4), nullable=True)
    notified_mrp = Column(Numeric(12, 4), nullable=True)
    unit = Column(String(100), nullable=False)  # 1 Tablet, 1 Capsule, 1 Injection, 100ml, etc.
    pack_size = Column(String(100), nullable=True)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=True, index=True)
    notification_number = Column(String(100), nullable=False, index=True)
    source_document = Column(String(255), nullable=False)
    source_page = Column(Integer, nullable=True)
    verification_status = Column(String(50), default="OFFICIAL_VERIFIED")  # OFFICIAL_VERIFIED, PROVISIONAL, UNVERIFIED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    medicine = relationship("Medicine", back_populates="pricing_records")
    audit_results = relationship("AuditResult", back_populates="pricing_record")
