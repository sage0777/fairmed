"""
FairMed Pytest Configuration and Test Fixtures
Provides an isolated in-memory test database, test client, and authenticated user headers.
"""

import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.medicine import Medicine
from app.models.medicine_alias import MedicineAlias
from app.models.source_document import SourceDocument
from app.models.pricing_record import PricingRecord
from app.security.password import hash_password
from app.security.jwt_handler import create_access_token

# In-memory SQLite for high-speed isolated testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed essential test medicines and pricing records
    src = SourceDocument(
        id="src-test-01",
        source_name="Gazette Notification S.O. 1499(E)",
        notification_number="S.O. 1499(E)",
        effective_date=date(2023, 4, 1),
        verification_status="VERIFIED"
    )
    db.add(src)

    m1 = Medicine(
        id="med-pcm-500",
        generic_name="Paracetamol 500mg Tablet",
        active_ingredients="Paracetamol",
        strength="500mg",
        dosage_form="Tablet",
        pack_size="Strip of 10 Tablets",
        category="DPCO_SCHEDULED_CEILING"
    )
    m2 = Medicine(
        id="med-pcm-650",
        generic_name="Paracetamol 650mg Tablet",
        active_ingredients="Paracetamol",
        strength="650mg",
        dosage_form="Tablet",
        pack_size="Strip of 15 Tablets",
        category="DPCO_SCHEDULED_CEILING"
    )
    m3 = Medicine(
        id="med-amox-625",
        generic_name="Amoxicillin + Clavulanic Acid 625mg Tablet",
        active_ingredients="Amoxicillin (500mg) + Clavulanic Acid (125mg)",
        strength="500mg + 125mg",
        dosage_form="Tablet",
        pack_size="Strip of 10 Tablets",
        category="DPCO_SCHEDULED_CEILING"
    )
    db.add_all([m1, m2, m3])
    db.flush()

    # Aliases
    a1 = MedicineAlias(medicine_id=m1.id, alias_name="Calpol 500", alias_type="BRAND")
    a2 = MedicineAlias(medicine_id=m2.id, alias_name="Dolo 650", alias_type="BRAND")
    a3 = MedicineAlias(medicine_id=m3.id, alias_name="Augmentin 625 Duo", alias_type="BRAND")
    db.add_all([a1, a2, a3])

    # Pricing Records
    p1 = PricingRecord(
        id="price-pcm-500",
        medicine_id=m1.id,
        pricing_category="DPCO_SCHEDULED_CEILING",
        ceiling_price=Decimal("1.01"),
        unit="1 Tablet",
        effective_from=date(2023, 4, 1),
        notification_number="S.O. 1499(E)",
        source_document="Gazette Notification S.O. 1499(E)",
        verification_status="OFFICIAL_VERIFIED"
    )
    p2 = PricingRecord(
        id="price-pcm-650",
        medicine_id=m2.id,
        pricing_category="DPCO_SCHEDULED_CEILING",
        ceiling_price=Decimal("2.04"),
        unit="1 Tablet",
        effective_from=date(2023, 4, 1),
        notification_number="S.O. 1499(E)",
        source_document="Gazette Notification S.O. 1499(E)",
        verification_status="OFFICIAL_VERIFIED"
    )
    p3 = PricingRecord(
        id="price-amox-625",
        medicine_id=m3.id,
        pricing_category="DPCO_SCHEDULED_CEILING",
        ceiling_price=Decimal("20.08"),
        unit="1 Tablet",
        effective_from=date(2023, 4, 1),
        notification_number="S.O. 1499(E)",
        source_document="Gazette Notification S.O. 1499(E)",
        verification_status="OFFICIAL_VERIFIED"
    )
    db.add_all([p1, p2, p3])

    # Test user
    u = User(
        id="user-test-01",
        full_name="Pytest Verified Patient",
        email="pytest.user@fairmed.org",
        password_hash=hash_password("PytestPassword123!")
    )
    db.add(u)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "user-test-01", "email": "pytest.user@fairmed.org"})
    return {"Authorization": f"Bearer {token}"}
