"""
FairMed Schemas - OCR and Extracted Medicine Items
Pydantic schemas for extracted bill medicine line items and corrections.
"""

from decimal import Decimal
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class ExtractedItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    extracted_medicine_name: str
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    extracted_strength: Optional[str] = None
    dosage_form: Optional[str] = None
    pack_size: Optional[str] = None
    quantity: Decimal = Field(default=Decimal("1.00"))
    billed_unit_price: Decimal
    billed_total: Decimal
    matched_medicine_id: Optional[str] = None
    confidence_score: float = 0.0
    verification_status: str = "PENDING_MATCH"  # PENDING_MATCH, MATCHED, UNCERTAIN, UNMATCHED


class ItemCorrectionRequest(BaseModel):
    extracted_medicine_name: Optional[str] = None
    extracted_strength: Optional[str] = None
    dosage_form: Optional[str] = None
    quantity: Optional[Decimal] = None
    billed_unit_price: Optional[Decimal] = None
    matched_medicine_id: Optional[str] = None


class OCRResultResponse(BaseModel):
    bill_id: str
    hospital_name: Optional[str] = None
    bill_date: Optional[date] = None
    total_items_extracted: int
    items: List[ExtractedItemSchema]
