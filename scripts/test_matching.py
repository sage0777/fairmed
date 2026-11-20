import sys
from pathlib import Path
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.repositories.medicine_repo import MedicineRepository
from app.engines.matching_engine import MedicineMatchingEngine

db = SessionLocal()
repo = MedicineRepository(db)
registry = repo.get_all_for_matching()
engine = MedicineMatchingEngine(registry)

test_cases = [
    "Dolo 650 Tab",
    "Calpol 500",
    "Augmentin 625 Duo",
    "Monocef 1g Inj",
    "Ciplox 500",
    "Pan 40",
    "RandomUnknownDrug 99"
]

print("\n--- MATCHING ENGINE TEST ---")
for q in test_cases:
    res = engine.match(q)
    cand_name = res.matched_candidate.generic_name if res.matched_candidate else "None"
    print(f"Query: '{q}' => Status: {res.verification_status}, Matched: '{cand_name}', Confidence: {res.overall_confidence}%")

db.close()
