"""
FairMed Bill Repository
Database operations for bills and extracted medicine line items.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.bill import Bill
from app.models.extracted_item import ExtractedItem


class BillRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, bill: Bill) -> Bill:
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def get_by_id(self, bill_id: str, user_id: Optional[str] = None) -> Optional[Bill]:
        query = self.db.query(Bill).options(
            joinedload(Bill.extracted_items),
            joinedload(Bill.audits)
        ).filter(Bill.id == bill_id)
        if user_id:
            query = query.filter(Bill.user_id == user_id)
        return query.first()

    def get_by_user(self, user_id: str) -> List[Bill]:
        return self.db.query(Bill).options(
            joinedload(Bill.extracted_items)
        ).filter(Bill.user_id == user_id).order_by(Bill.upload_date.desc()).all()

    def delete(self, bill: Bill) -> bool:
        self.db.delete(bill)
        self.db.commit()
        return True

    def add_extracted_items(self, items: List[ExtractedItem]) -> List[ExtractedItem]:
        self.db.add_all(items)
        self.db.commit()
        return items

    def get_extracted_items(self, bill_id: str) -> List[ExtractedItem]:
        return self.db.query(ExtractedItem).filter(
            ExtractedItem.bill_id == bill_id
        ).all()

    def get_extracted_item_by_id(self, item_id: str) -> Optional[ExtractedItem]:
        return self.db.query(ExtractedItem).filter(ExtractedItem.id == item_id).first()
