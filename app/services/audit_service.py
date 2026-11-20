"""
FairMed Audit Service
Coordinates the deterministic auditing of extracted bill items against NPPA pricing records.
"""

from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone, date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.audit import Audit
from app.models.audit_result import AuditResult
from app.models.user import User
from app.repositories.bill_repo import BillRepository
from app.repositories.audit_repo import AuditRepository
from app.repositories.pricing_repo import PricingRepository
from app.repositories.medicine_repo import MedicineRepository
from app.engines.pricing_engine import NPPAPricingEngine


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.bill_repo = BillRepository(db)
        self.audit_repo = AuditRepository(db)
        self.pricing_repo = PricingRepository(db)
        self.med_repo = MedicineRepository(db)

    def run_bill_audit(self, bill_id: str, user: User) -> Audit:
        """Executes regulatory price evaluation for all items in a bill."""
        bill = self.bill_repo.get_by_id(bill_id, user_id=user.id)
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found or you do not have permission to access it."
            )

        items = bill.extracted_items
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bill has no extracted items. Run OCR extraction (/api/ocr/extract/{bill_id}) first."
            )

        # Create audit container
        audit = Audit(
            bill_id=bill.id,
            audit_date=datetime.now(timezone.utc),
            total_items=len(items),
            verified_items=0,
            flagged_items=0,
            total_potential_difference=Decimal("0.00"),
            audit_status="COMPLETED"
        )
        self.db.add(audit)
        self.db.flush()

        verified_count = 0
        flagged_count = 0
        total_difference = Decimal("0.00")
        results: List[AuditResult] = []

        ref_date = bill.bill_date or date.today()

        for itm in items:
            med = None
            pricing_rec = None
            is_verified = (itm.verification_status == "MATCHED")

            if itm.matched_medicine_id:
                med = self.med_repo.get_by_id(itm.matched_medicine_id)
                if med:
                    pricing_rec = self.pricing_repo.get_effective_price(med.id, target_date=ref_date)

            # Evaluate with deterministic Python pricing engine
            calc = NPPAPricingEngine.evaluate_price(
                billed_unit_price=Decimal(str(itm.billed_unit_price)),
                quantity=Decimal(str(itm.quantity)),
                medicine=med,
                pricing_record=pricing_rec,
                is_verified_match=is_verified,
                pack_size=itm.dosage_form,
                bill_date=ref_date
            )

            if calc.result_status == "OVERCHARGED":
                flagged_count += 1
                total_difference += calc.total_difference
            if calc.result_status in ("OVERCHARGED", "COMPLIANT"):
                verified_count += 1

            audit_res = AuditResult(
                audit_id=audit.id,
                extracted_item_id=itm.id,
                pricing_record_id=calc.pricing_record_id,
                billed_price=calc.billed_unit_price,
                reference_price=calc.reference_price,
                price_difference=calc.price_difference,
                quantity=calc.quantity,
                total_difference=calc.total_difference,
                result_status=calc.result_status,
                explanation=calc.explanation
            )
            results.append(audit_res)

        self.db.add_all(results)
        
        # Update audit totals
        audit.verified_items = verified_count
        audit.flagged_items = flagged_count
        audit.total_potential_difference = total_difference
        bill.status = "AUDITED"

        self.db.commit()
        self.db.refresh(audit)
        return audit
