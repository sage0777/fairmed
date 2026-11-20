"""
Integration tests for FastAPI REST endpoints and end-to-end bill audit flow.
"""

from decimal import Decimal


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_medicine_search_api(client):
    res = client.get("/api/medicines/search?q=Paracetamol")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2


def test_medicine_match_api(client):
    res = client.get("/api/medicines/match?q=Dolo 650 Tab")
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == "MATCHED"
    assert data["matched_candidate"]["generic_name"] == "Paracetamol 650mg Tablet"


def test_standalone_pricing_check_api(client):
    # Standalone price check for Dolo 650 at Rs.5.50
    res = client.get("/api/pricing/check?medicine_name=Dolo 650&billed_unit_price=5.50&quantity=10")
    assert res.status_code == 200
    data = res.json()
    assert data["result_status"] == "OVERCHARGED"
    assert Decimal(str(data["reference_ceiling_price"])) == Decimal("2.04")
    assert Decimal(str(data["price_difference_per_unit"])) == Decimal("3.46")
    assert Decimal(str(data["total_difference"])) == Decimal("34.60")
