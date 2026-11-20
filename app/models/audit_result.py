import uuid
from sqlalchemy import Column, String, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id = Column(String(36), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_item_id = Column(String(36), ForeignKey("extracted_items.id", ondelete="CASCADE"), nullable=False)
    pricing_record_id = Column(String(36), ForeignKey("pricing_records.id", ondelete="SET NULL"), nullable=True, index=True)
    billed_price = Column(Numeric(12, 4), nullable=False)
    reference_price = Column(Numeric(12, 4), nullable=True)
    price_difference = Column(Numeric(12, 4), default=0.00)
    quantity = Column(Numeric(10, 2), nullable=False, default=1.00)
    total_difference = Column(Numeric(12, 4), default=0.00)
    result_status = Column(String(50), nullable=False)  # COMPLIANT, OVERCHARGED, NO_CEILING_APPLICABLE, INSUFFICIENT_DATA
    explanation = Column(Text, nullable=True)

    audit = relationship("Audit", back_populates="results")
    extracted_item = relationship("ExtractedItem", back_populates="audit_results")
    pricing_record = relationship("PricingRecord", back_populates="audit_results")
