"""
FairMed OCR Router
Endpoints for triggering OCR extraction on uploaded bills and fetching structured medicine line items.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.ocr import OCRResultResponse, ExtractedItemSchema, ItemCorrectionRequest
from app.services.bill_service import BillService
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api/ocr", tags=["OCR & Extraction"])


@router.post("/extract/{bill_id}", response_model=OCRResultResponse)
def trigger_ocr_extraction(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers OCR text parsing and medicine item extraction for a previously uploaded bill.
    Automatically identifies medicine names, strengths, quantities, and billed prices.
    """
    bill_svc = BillService(db)
    bill = bill_svc.extract_and_match_bill(bill_id, current_user)
    
    items = bill_svc.bill_repo.get_extracted_items(bill.id)
    return OCRResultResponse(
        bill_id=bill.id,
        hospital_name=bill.hospital_name,
        bill_date=bill.bill_date,
        total_items_extracted=len(items),
        items=[ExtractedItemSchema.model_validate(i) for i in items]
    )


@router.get("/results/{bill_id}", response_model=OCRResultResponse)
def get_ocr_results(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the extracted medicine items and OCR results for a bill."""
    bill_svc = BillService(db)
    bill = bill_svc.bill_repo.get_by_id(bill_id, user_id=current_user.id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found."
        )

    items = bill_svc.bill_repo.get_extracted_items(bill.id)
    return OCRResultResponse(
        bill_id=bill.id,
        hospital_name=bill.hospital_name,
        bill_date=bill.bill_date,
        total_items_extracted=len(items),
        items=[ExtractedItemSchema.model_validate(i) for i in items]
    )


@router.put("/items/{item_id}", response_model=ExtractedItemSchema)
def update_extracted_item(
    item_id: str,
    req: ItemCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows the user to correct or verify extracted details (e.g. spelling, strength, quantity)
    prior to running the regulatory pricing audit.
    """
    bill_svc = BillService(db)
    item = bill_svc.bill_repo.get_extracted_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted line item not found."
        )

    # Verify user owns the bill
    bill = bill_svc.bill_repo.get_by_id(item.bill_id, user_id=current_user.id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this item."
        )

    if req.extracted_medicine_name is not None:
        item.extracted_medicine_name = req.extracted_medicine_name
    if req.extracted_strength is not None:
        item.extracted_strength = req.extracted_strength
    if req.dosage_form is not None:
        item.dosage_form = req.dosage_form
    if req.quantity is not None:
        item.quantity = req.quantity
    if req.billed_unit_price is not None:
        item.billed_unit_price = req.billed_unit_price
        item.billed_total = item.billed_unit_price * item.quantity
    if req.matched_medicine_id is not None:
        item.matched_medicine_id = req.matched_medicine_id
        item.verification_status = "MATCHED"

    db.commit()
    db.refresh(item)
    return ExtractedItemSchema.model_validate(item)
