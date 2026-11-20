import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ExtractedItem(Base):
    __tablename__ = "extracted_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_medicine_name = Column(String(255), nullable=False)
    extracted_strength = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False, default=1.00)
    billed_unit_price = Column(Numeric(12, 4), nullable=False)
    billed_total = Column(Numeric(12, 4), nullable=False)
    matched_medicine_id = Column(String(36), ForeignKey("medicines.id", ondelete="SET NULL"), nullable=True, index=True)
    confidence_score = Column(Numeric(5, 2), default=0.00)
    verification_status = Column(String(50), default="PENDING_MATCH")  # PENDING_MATCH, MATCHED, UNMATCHED, UNCERTAIN

    bill = relationship("Bill", back_populates="extracted_items")
    matched_medicine = relationship("Medicine", back_populates="extracted_items")
    audit_results = relationship("AuditResult", back_populates="extracted_item", cascade="all, delete-orphan")
