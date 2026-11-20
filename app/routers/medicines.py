"""
FairMed Medicines Router
Endpoints for medicine search, detail retrieval, fuzzy matching, and pricing records.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.medicine import (
    MedicineSummarySchema,
    MedicineDetailResponse,
    MedicineMatchResponse,
    PricingRecordSchema
)
from app.repositories.medicine_repo import MedicineRepository
from app.engines.matching_engine import MedicineMatchingEngine

router = APIRouter(prefix="/api/medicines", tags=["Medicines"])


@router.get("/search", response_model=List[MedicineSummarySchema])
def search_medicines(
    q: str = Query(..., min_length=2, description="Search query by brand, generic, or ingredient"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Searches the official medicine master database by generic, brand, or active ingredient."""
    repo = MedicineRepository(db)
    results = repo.search_by_name(q, limit=limit)
    return [MedicineSummarySchema.model_validate(m) for m in results]


@router.get("/match", response_model=MedicineMatchResponse)
def match_medicine_query(
    q: str = Query(..., min_length=2, description="Raw medicine string from bill (e.g. 'Dolo 650 Tab')"),
    db: Session = Depends(get_db)
):
    """
    Performs RapidFuzz token matching, strength verification, and dosage validation
    on an arbitrary query string against the official medicine registry.
    """
    repo = MedicineRepository(db)
    registry = repo.get_all_for_matching()
    engine = MedicineMatchingEngine(registry)
    result = engine.match(q)

    return MedicineMatchResponse(
        query=q,
        matched_candidate=result.matched_candidate,
        alternatives=result.alternatives,
        overall_confidence=result.overall_confidence,
        verification_status=result.verification_status,
        explanation=result.explanation
    )


@router.get("/{medicine_id}", response_model=MedicineDetailResponse)
def get_medicine_detail(
    medicine_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves full details of a medicine, including registered brand aliases and regulatory price history."""
    repo = MedicineRepository(db)
    med = repo.get_by_id(medicine_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found."
        )

    aliases = [a.alias_name for a in med.aliases]
    prices = [PricingRecordSchema.model_validate(p) for p in med.pricing_records]

    return MedicineDetailResponse(
        id=med.id,
        generic_name=med.generic_name,
        brand_name=med.brand_name,
        active_ingredients=med.active_ingredients,
        strength=med.strength,
        dosage_form=med.dosage_form,
        pack_size=med.pack_size,
        category=med.category,
        aliases=aliases,
        pricing_records=prices
    )


@router.get("/{medicine_id}/prices", response_model=List[PricingRecordSchema])
def get_medicine_pricing_records(
    medicine_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves all official NPPA regulatory ceiling and notified price records for a specific medicine."""
    repo = MedicineRepository(db)
    prices = repo.get_pricing_records(medicine_id)
    return [PricingRecordSchema.model_validate(p) for p in prices]
