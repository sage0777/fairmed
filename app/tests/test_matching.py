"""
Unit tests for medicine name normalization, RapidFuzz matching, and strength verification.
"""

from app.repositories.medicine_repo import MedicineRepository
from app.engines.matching_engine import MedicineMatchingEngine
from app.utils.normalizer import extract_strength, standardize_dosage_form, parse_medicine_components
from app.utils.unit_converter import parse_pack_size_count, normalize_to_unit_price


def test_normalizer_utilities():
    assert extract_strength("Dolo 650 Tab") == "650mg"
    assert extract_strength("Calpol 500") == "500mg"
    assert extract_strength("Augmentin 625 Duo") == "625mg"
    assert extract_strength("Monocef 1g Inj") == "1g"

    assert standardize_dosage_form("TAB DOLO") == "Tablet"
    assert standardize_dosage_form("INJ MONOCEF") == "Injection"
    assert standardize_dosage_form("SYR CALPOL") == "Oral Liquid / Syrup"

    assert parse_pack_size_count("Strip of 10") == 10
    assert parse_pack_size_count("1 x 15") == 15
    assert parse_pack_size_count("1 Vial") == 1


def test_medicine_matching_exact_alias(db_session):
    repo = MedicineRepository(db_session)
    registry = repo.get_all_for_matching()
    engine = MedicineMatchingEngine(registry)

    # Dolo 650 -> Paracetamol 650mg
    res1 = engine.match("Dolo 650 Tab")
    assert res1.verification_status == "MATCHED"
    assert res1.matched_candidate.generic_name == "Paracetamol 650mg Tablet"
    assert res1.matched_candidate.strength_match is True

    # Calpol 500 -> Paracetamol 500mg
    res2 = engine.match("Calpol 500")
    assert res2.verification_status == "MATCHED"
    assert res2.matched_candidate.generic_name == "Paracetamol 500mg Tablet"

    # Augmentin 625 Duo -> Amoxicillin + Clavulanic
    res3 = engine.match("Augmentin 625 Duo")
    assert res3.verification_status == "MATCHED"
    assert res3.matched_candidate.generic_name == "Amoxicillin + Clavulanic Acid 625mg Tablet"


def test_medicine_matching_strength_isolation(db_session):
    repo = MedicineRepository(db_session)
    registry = repo.get_all_for_matching()
    engine = MedicineMatchingEngine(registry)

    # Query with 650mg must NOT be matched to a 500mg formulation
    res = engine.match("Paracetamol 650mg")
    assert res.matched_candidate.strength == "650mg"
    assert res.matched_candidate.generic_name == "Paracetamol 650mg Tablet"


def test_medicine_matching_unknown_drug(db_session):
    repo = MedicineRepository(db_session)
    registry = repo.get_all_for_matching()
    engine = MedicineMatchingEngine(registry)

    res = engine.match("Xylophonic Unknown NonExistentDrug 999")
    assert res.verification_status == "UNMATCHED"
    assert res.matched_candidate is None
