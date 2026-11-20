"""
FairMed Schemas - Audit & Pricing Check
Pydantic schemas for auditing bills, results, and standalone regulatory price checks.
"""

from decimal import Decimal
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class AuditResultItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    extracted_item_id: str
    medicine_name: str
    extracted_strength: Optional[str] = None
    dosage_form: Optional[str] = None
    quantity: Decimal
    billed_price: Decimal
    reference_price: Optional[Decimal] = None
    price_difference: Decimal
    total_difference: Decimal
    result_status: str  # OVERCHARGED, COMPLIANT, NO_CEILING_APPLICABLE, INSUFFICIENT_DATA
    regulatory_source: Optional[str] = None
    notification_number: Optional[str] = None
    explanation: Optional[str] = None


class AuditSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bill_id: str
    audit_date: datetime
    total_items: int
    verified_items: int
    flagged_items: int
    total_potential_difference: Decimal
    audit_status: str


class AuditDetailResponse(BaseModel):
    audit: AuditSummaryResponse
    results: List[AuditResultItemSchema]


class PricingCheckRequest(BaseModel):
    medicine_name: str
    billed_unit_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    bill_date: Optional[date] = None
    pack_size: Optional[str] = None


class PricingCheckResponse(BaseModel):
    query: str
    matched_medicine: Optional[str] = None
    matched_strength: Optional[str] = None
    billed_unit_price: Decimal
    quantity: Decimal
    billed_total: Decimal
    reference_ceiling_price: Optional[Decimal] = None
    allowable_with_gst: Optional[Decimal] = None
    price_difference_per_unit: Decimal
    total_difference: Decimal
    result_status: str
    notification_number: Optional[str] = None
    source_document: Optional[str] = None
    explanation: str
