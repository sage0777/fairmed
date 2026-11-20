"""
FairMed Pricing Repository
Database retrieval functions for regulatory price records and effective-date evaluation.
"""

from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.pricing_record import PricingRecord


class PricingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_effective_price(
        self,
        medicine_id: str,
        target_date: Optional[date] = None
    ) -> Optional[PricingRecord]:
        """
        Retrieves the legally active pricing record for a given medicine on a specific bill date.
        If target_date is None, defaults to current date.
        Ensures superseded past notifications or un-notified future dates are not applied erroneously.
        """
        ref_date = target_date or date.today()

        query = self.db.query(PricingRecord).filter(
            PricingRecord.medicine_id == medicine_id,
            PricingRecord.effective_from <= ref_date,
            or_(
                PricingRecord.effective_to.is_(None),
                PricingRecord.effective_to >= ref_date
            )
        ).order_by(PricingRecord.effective_from.desc())

        return query.first()

    def get_all_records_for_medicine(self, medicine_id: str) -> List[PricingRecord]:
        return self.db.query(PricingRecord).filter(
            PricingRecord.medicine_id == medicine_id
        ).order_by(PricingRecord.effective_from.desc()).all()
