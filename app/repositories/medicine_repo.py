"""
FairMed Medicine Repository
Database operations for medicines, aliases, and regulatory price relations.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, select

from app.models.medicine import Medicine
from app.models.medicine_alias import MedicineAlias
from app.models.pricing_record import PricingRecord


class MedicineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, medicine_id: str) -> Optional[Medicine]:
        return self.db.query(Medicine).options(
            joinedload(Medicine.aliases),
            joinedload(Medicine.pricing_records)
        ).filter(Medicine.id == medicine_id).first()

    def search_by_name(self, query: str, limit: int = 20) -> List[Medicine]:
        clean_q = f"%{query.strip()}%"
        return self.db.query(Medicine).filter(
            or_(
                Medicine.generic_name.ilike(clean_q),
                Medicine.brand_name.ilike(clean_q),
                Medicine.active_ingredients.ilike(clean_q)
            )
        ).limit(limit).all()

    def get_all_for_matching(self) -> List[Tuple[Medicine, List[str]]]:
        """
        Retrieves all medicines with their known brand and generic aliases for rapid in-memory fuzzy matching.
        """
        medicines = self.db.query(Medicine).options(joinedload(Medicine.aliases)).all()
        result = []
        for med in medicines:
            alias_list = [a.alias_name for a in med.aliases]
            result.append((med, alias_list))
        return result

    def get_pricing_records(self, medicine_id: str) -> List[PricingRecord]:
        return self.db.query(PricingRecord).filter(
            PricingRecord.medicine_id == medicine_id
        ).order_by(PricingRecord.effective_from.desc()).all()
