"""
FairMed Schemas - Medicine & Matching
Pydantic schemas for medicine lookup, fuzzy matching, and pricing records.
"""

from decimal import Decimal
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, ConfigDict
from app.engines.matching_engine import MatchCandidate


class PricingRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pricing_category: str
    price_type: str
    ceiling_price: Optional[Decimal] = None
    notified_mrp: Optional[Decimal] = None
    unit: str
    pack_size: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    notification_number: str
    source_document: str
    verification_status: str


class MedicineSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    generic_name: str
    brand_name: Optional[str] = None
    active_ingredients: str
    strength: str
    dosage_form: str
    pack_size: Optional[str] = None
    category: Optional[str] = None


class MedicineDetailResponse(MedicineSummarySchema):
    aliases: List[str] = []
    pricing_records: List[PricingRecordSchema] = []


class MedicineMatchRequest(BaseModel):
    query: str
    extracted_strength: Optional[str] = None
    dosage_form: Optional[str] = None


class MedicineMatchResponse(BaseModel):
    query: str
    matched_candidate: Optional[MatchCandidate] = None
    alternatives: List[MatchCandidate] = []
    overall_confidence: float
    verification_status: str
    explanation: str
