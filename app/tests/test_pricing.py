"""
Unit tests for deterministic NPPA pricing calculations, GST adjustments, and effective-date selection.
"""

from decimal import Decimal
from datetime import date
from app.repositories.medicine_repo import MedicineRepository
from app.repositories.pricing_repo import PricingRepository
from app.engines.pricing_engine import NPPAPricingEngine


def test_pricing_overcharged_calculation(db_session):
    med_repo = MedicineRepository(db_session)
    price_repo = PricingRepository(db_session)

    med = med_repo.get_by_id("med-pcm-500")
    pricing_rec = price_repo.get_effective_price(med.id, date(2023, 6, 1))

    # Billed Rs.5.00 vs Rs.1.01 ceiling
    calc = NPPAPricingEngine.evaluate_price(
        billed_unit_price=Decimal("5.00"),
        quantity=Decimal("10"),
        medicine=med,
        pricing_record=pricing_rec,
        is_verified_match=True,
        bill_date=date(2023, 6, 1)
    )

    assert calc.result_status == "OVERCHARGED"
    assert calc.reference_price == Decimal("1.01")
    assert calc.price_difference == Decimal("3.99")
    assert calc.total_difference == Decimal("39.90")
    assert "S.O. 1499(E)" in calc.explanation


def test_pricing_compliant_calculation(db_session):
    med_repo = MedicineRepository(db_session)
    price_repo = PricingRepository(db_session)

    med = med_repo.get_by_id("med-pcm-650")
    pricing_rec = price_repo.get_effective_price(med.id, date(2023, 6, 1))

    # Billed Rs.2.00 (within Rs.2.04 ceiling)
    calc = NPPAPricingEngine.evaluate_price(
        billed_unit_price=Decimal("2.00"),
        quantity=Decimal("15"),
        medicine=med,
        pricing_record=pricing_rec,
        is_verified_match=True,
        bill_date=date(2023, 6, 1)
    )

    assert calc.result_status == "COMPLIANT"
    assert calc.price_difference == Decimal("0.00")
    assert calc.total_difference == Decimal("0.00")


def test_pricing_effective_date_boundary(db_session):
    price_repo = PricingRepository(db_session)

    # Date prior to notification (before 2023-04-01)
    past_price = price_repo.get_effective_price("med-pcm-500", date(2020, 1, 1))
    assert past_price is None

    # Date on or after notification
    active_price = price_repo.get_effective_price("med-pcm-500", date(2023, 4, 1))
    assert active_price is not None
    assert active_price.notification_number == "S.O. 1499(E)"
