import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.repositories.medicine_repo import MedicineRepository
from app.repositories.pricing_repo import PricingRepository
from app.engines.pricing_engine import NPPAPricingEngine

db = SessionLocal()
med_repo = MedicineRepository(db)
price_repo = PricingRepository(db)

# Look up Paracetamol 500mg
meds = med_repo.search_by_name("Paracetamol 500mg", limit=1)
if not meds:
    print("[!] Paracetamol 500mg not found in database!")
    sys.exit(1)

med = meds[0]
pricing_record = price_repo.get_effective_price(med.id, date(2023, 6, 1))

print("=== NPPA PRICING ENGINE TESTS ===")

# Test 1: Overcharged case (Billed ₹5.00 vs ₹1.01 ceiling)
calc1 = NPPAPricingEngine.evaluate_price(
    billed_unit_price=Decimal("5.00"),
    quantity=Decimal("10"),
    medicine=med,
    pricing_record=pricing_record,
    is_verified_match=True,
    bill_date=date(2023, 6, 1)
)
print(f"Test 1 (Overcharged): Status={calc1.result_status}, RefPrice={calc1.reference_price}, DiffPerUnit={calc1.price_difference}, TotalDiff={calc1.total_difference}")
assert calc1.result_status == "OVERCHARGED"
assert calc1.total_difference == Decimal("39.90")

# Test 2: Compliant case (Billed ₹1.00 vs ₹1.01 ceiling)
calc2 = NPPAPricingEngine.evaluate_price(
    billed_unit_price=Decimal("1.00"),
    quantity=Decimal("10"),
    medicine=med,
    pricing_record=pricing_record,
    is_verified_match=True,
    bill_date=date(2023, 6, 1)
)
print(f"Test 2 (Compliant): Status={calc2.result_status}, RefPrice={calc2.reference_price}, DiffPerUnit={calc2.price_difference}, TotalDiff={calc2.total_difference}")
assert calc2.result_status == "COMPLIANT"
assert calc2.total_difference == Decimal("0.00")

# Test 3: Unverified match case
calc3 = NPPAPricingEngine.evaluate_price(
    billed_unit_price=Decimal("5.00"),
    quantity=Decimal("10"),
    medicine=med,
    pricing_record=pricing_record,
    is_verified_match=False,
    bill_date=date(2023, 6, 1)
)
print(f"Test 3 (Unverified): Status={calc3.result_status}, Explanation={calc3.explanation}")
assert calc3.result_status == "INSUFFICIENT_DATA"

# Test 4: No ceiling record case
calc4 = NPPAPricingEngine.evaluate_price(
    billed_unit_price=Decimal("100.00"),
    quantity=Decimal("1"),
    medicine=med,
    pricing_record=None,
    is_verified_match=True,
    bill_date=date(2023, 6, 1)
)
print(f"Test 4 (No Ceiling): Status={calc4.result_status}, Explanation={calc4.explanation[:50]}...")
assert calc4.result_status == "NO_CEILING_APPLICABLE"

print("\n[+] All pricing engine assertions passed successfully!")
db.close()
