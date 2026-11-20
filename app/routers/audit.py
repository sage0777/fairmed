"""
FairMed Audit Router
Endpoints for running bill audits, retrieving audit results, and standalone regulatory price checks.
"""

from decimal import Decimal
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.audit import (
    AuditSummaryResponse,
    AuditDetailResponse,
    AuditResultItemSchema,
    PricingCheckResponse
)
from app.services.audit_service import AuditService
from app.repositories.audit_repo import AuditRepository
from app.repositories.medicine_repo import MedicineRepository
from app.repositories.pricing_repo import PricingRepository
from app.engines.matching_engine import MedicineMatchingEngine
from app.engines.pricing_engine import NPPAPricingEngine
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Pricing & Audit"])


@router.post("/api/audit/{bill_id}", response_model=AuditSummaryResponse, status_code=status.HTTP_201_CREATED)
def run_audit(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes the deterministic NPPA regulatory pricing audit on all items in a bill.
    Identifies potential discrepancies against official DPCO ceiling prices valid on the bill date.
    """
    audit_svc = AuditService(db)
    audit = audit_svc.run_bill_audit(bill_id, current_user)
    return AuditSummaryResponse.model_validate(audit)


@router.get("/api/audit/{audit_id}", response_model=AuditSummaryResponse)
def get_audit_summary(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves high-level summary metrics of an audit."""
    audit_repo = AuditRepository(db)
    audit = audit_repo.get_by_id(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found."
        )

    # Security check: User owns parent bill
    if audit.bill.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this audit."
        )

    return AuditSummaryResponse.model_validate(audit)


@router.get("/api/audit/{audit_id}/results", response_model=List[AuditResultItemSchema])
def get_audit_results(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the item-by-item discrepancy results with regulatory references for an audit."""
    audit_repo = AuditRepository(db)
    audit = audit_repo.get_by_id(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found."
        )

    if audit.bill.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view these audit results."
        )

    output = []
    for r in audit.results:
        ext = r.extracted_item
        pr = r.pricing_record
        output.append(
            AuditResultItemSchema(
                id=r.id,
                extracted_item_id=r.extracted_item_id,
                medicine_name=ext.extracted_medicine_name if ext else "Unknown",
                extracted_strength=ext.extracted_strength if ext else None,
                dosage_form=ext.dosage_form if ext else None,
                quantity=r.quantity,
                billed_price=r.billed_price,
                reference_price=r.reference_price,
                price_difference=r.price_difference,
                total_difference=r.total_difference,
                result_status=r.result_status,
                regulatory_source=pr.source_document if pr else None,
                notification_number=pr.notification_number if pr else None,
                explanation=r.explanation
            )
        )
    return output


@router.get("/api/pricing/check", response_model=PricingCheckResponse)
def check_standalone_price(
    medicine_name: str = Query(..., min_length=2, description="Name or brand of medicine (e.g. 'Dolo 650' or 'Pan 40')"),
    billed_unit_price: Decimal = Query(..., gt=0, description="Unit price charged by pharmacy/hospital"),
    quantity: Decimal = Query(Decimal("1.00"), gt=0, description="Quantity billed"),
    bill_date: Optional[date] = Query(None, description="Date of transaction (defaults to today)"),
    db: Session = Depends(get_db)
):
    """
    Direct regulatory pricing evaluation endpoint for patients to check any medicine price
    against official NPPA ceiling limits in real-time without uploading a document.
    """
    med_repo = MedicineRepository(db)
    price_repo = PricingRepository(db)

    # 1. Match medicine
    registry = med_repo.get_all_for_matching()
    engine = MedicineMatchingEngine(registry)
    match_res = engine.match(medicine_name)

    target_date = bill_date or date.today()
    med_obj = None
    pricing_rec = None
    is_verified = (match_res.verification_status == "MATCHED")

    if match_res.matched_candidate:
        med_obj = med_repo.get_by_id(match_res.matched_candidate.medicine_id)
        if med_obj:
            pricing_rec = price_repo.get_effective_price(med_obj.id, target_date=target_date)

    # 2. Evaluate with deterministic NPPA engine
    calc = NPPAPricingEngine.evaluate_price(
        billed_unit_price=billed_unit_price,
        quantity=quantity,
        medicine=med_obj,
        pricing_record=pricing_rec,
        is_verified_match=is_verified,
        bill_date=target_date
    )

    return PricingCheckResponse(
        query=medicine_name,
        matched_medicine=med_obj.generic_name if med_obj else None,
        matched_strength=med_obj.strength if med_obj else None,
        billed_unit_price=calc.billed_unit_price,
        quantity=calc.quantity,
        billed_total=calc.billed_total,
        reference_ceiling_price=calc.reference_price,
        allowable_with_gst=calc.allowable_ceiling_with_gst,
        price_difference_per_unit=calc.price_difference,
        total_difference=calc.total_difference,
        result_status=calc.result_status,
        notification_number=calc.notification_number,
        source_document=calc.source_document,
        explanation=calc.explanation
    )
