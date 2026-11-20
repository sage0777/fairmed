# FairMed – AI-Powered Medical Bill Auditing System Backend

FairMed is a production-grade backend engine designed to help patients, legal advocates, and consumer health organizations audit hospital medical bills against official Government of India (NPPA / DPCO 2013 / NLEM) ceiling prices, trade margin caps, and verified MRP records.

> **Core Principle:** AI extracts and assists with noisy text and entity identification; verified regulatory data and deterministic Python logic perform the price verification and calculate legal overcharges.

---

## 1. System Architecture

```mermaid
flowchart TD
    User([User / Patient]) -->|1. Uploads Bill Image / PDF| API[FastAPI REST API Gateway]
    API --> Auth[JWT & Auth Middleware]
    API --> Storage[(Secure File Storage)]
    API --> OCR[OCR Pipeline\nOpenCV + PyPDF / PaddleOCR]
    OCR --> Parsing[Item Extractor\nName, Strength, Dosage, Qty, Rate, Total]
    Parsing --> MatchEngine[Medicine Matching Engine\nRapidFuzz + Strength & Dosage Verifier]
    MatchEngine <--> MedRepo[(PostgreSQL Medicine Master & Aliases)]
    MatchEngine --> PriceEngine[Deterministic NPPA Pricing Engine\nEffective-Date & Unit Normalizer]
    PriceEngine <--> PriceRepo[(NPPA DPCO Pricing Records & Notifications)]
    PriceEngine --> AuditGen[Audit & Discrepancy Calculator]
    AuditGen --> DB[(Audits & Discrepancy Results)]
    AuditGen --> ReportGen[ReportLab PDF Grievance Generator]
    ReportGen --> GrievancePDF[Formal Grievance Petition PDF]
    GrievancePDF --> User
```

---

## 2. Technology Stack

| Component | Technology | Description |
|---|---|---|
| Language | Python 3.10+ (Tested on 3.14) | High-performance core backend |
| Web Framework | FastAPI | Asynchronous REST APIs with OpenAPI / Swagger docs |
| Database | Supabase + PostgreSQL | Relational persistence with Row Level Security (RLS) |
| Local Fallback | SQLite | Instant local development and test suite without setup |
| ORM | SQLAlchemy 2.0 | Declarative models and relationships |
| Fuzzy Matching | RapidFuzz | Token sort ratio & token set ratio string matching |
| OCR Integration | PyPDF & OpenCV (PaddleOCR pluggable) | Text extraction & image binarization pipeline |
| PDF Reporting | ReportLab | Evidentiary audit summaries & grievance petitions |
| Validation | Pydantic v2 | Robust input/output schemas |
| Security | PyJWT & Bcrypt | JWT authentication and salted password hashing |
| Test Runner | Pytest | Comprehensive unit and integration test suite |

---

## 3. Directory Layout

```
fairmed-backend/
├── app/
│   ├── main.py                  # Application entry point, CORS, routers & health check
│   ├── config.py                # Pydantic Settings and environment configurations
│   ├── database.py              # SQLAlchemy engine, session maker, Base definition
│   ├── models/                  # 9 PostgreSQL / Supabase ORM tables
│   │   ├── user.py              # User accounts
│   │   ├── medicine.py          # Medicine master data
│   │   ├── medicine_alias.py    # Registered brand and spelling aliases
│   │   ├── source_document.py   # NPPA Gazette notifications & URLs
│   │   ├── pricing_record.py    # Official DPCO ceiling prices with effective dates
│   │   ├── bill.py              # Uploaded medical bills
│   │   ├── extracted_item.py    # Extracted medicine line items
│   │   ├── audit.py             # Audit run headers and summary metrics
│   │   └── audit_result.py      # Item-by-item discrepancy calculations
│   ├── schemas/                 # Pydantic validation models
│   │   ├── auth.py
│   │   ├── bill.py
│   │   ├── ocr.py
│   │   ├── medicine.py
│   │   ├── audit.py
│   │   └── report.py
│   ├── engines/                 # Pure domain business engines
│   │   ├── matching_engine.py   # RapidFuzz matcher + strength/formulation verifier
│   │   └── pricing_engine.py    # Deterministic NPPA regulatory price calculator
│   ├── repositories/            # Database query layers
│   │   ├── medicine_repo.py
│   │   ├── pricing_repo.py
│   │   ├── bill_repo.py
│   │   └── audit_repo.py
│   ├── services/                # Business logic orchestrators
│   │   ├── auth_service.py
│   │   ├── bill_service.py
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   └── dataset_service.py
│   ├── integrations/            # Document extraction & OCR
│   │   └── ocr_pipeline.py      # OpenCV image enhancement + PyPDF table parsing
│   ├── routers/                 # REST API endpoints
│   │   ├── auth.py
│   │   ├── bills.py
│   │   ├── ocr.py
│   │   ├── medicines.py
│   │   ├── audit.py
│   │   └── reports.py
│   ├── middleware/              # Global JSON error handling
│   │   └── error_handler.py
│   ├── security/                # Bcrypt passwords & JWT handler
│   │   ├── password.py
│   │   ├── jwt_handler.py
│   │   └── dependencies.py
│   ├── utils/                   # Text normalizer and unit converter
│   │   ├── normalizer.py
│   │   └── unit_converter.py
│   └── tests/                   # Pytest suite
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_matching.py
│       ├── test_pricing.py
│       └── test_api_flow.py
├── datasets/
│   ├── nppa_official/           # Official NPPA DPCO price gazette notifications
│   │   ├── dpco_nlem_scheduled_ceiling_prices.json
│   │   └── oncology_trade_margin_capped.json
│   ├── dataset_import_report.md
│   └── sample_hospital_bill.pdf
├── scripts/
│   ├── ingest_nppa_data.py      # Official NPPA dataset ingestion CLI
│   ├── seed_sample_bills.py     # Sample medical bill generator
│   └── run_audit_cli.py         # End-to-end CLI validation pipeline
├── migrations/
│   ├── 001_initial_schema.sql   # PostgreSQL / Supabase full schema DDL
│   └── 002_rls_policies.sql     # Supabase Row Level Security policies
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

---

## 4. Setup & Installation

### Step 1: Install Python Dependencies
```bash
cd fairmed-backend
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy the template `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key variables:
- `DATABASE_URL`: `sqlite:///./fairmed.db` (default local) or `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres` (for Supabase PostgreSQL)
- `JWT_SECRET_KEY`: Set your secret key
- `SUPABASE_URL` / `SUPABASE_KEY`: Optional for Supabase Auth/Storage

### Step 3: Run Database Migrations & Ingest NPPA Data
Execute the NPPA dataset ingestion script. This automatically creates all tables and ingests official ceiling price notifications:
```bash
python scripts/ingest_nppa_data.py
```

### Step 4: Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to view the interactive Swagger OpenAPI documentation.

---

## 5. API Reference Summary

### Authentication APIs
- `POST /api/auth/register` – Register a user account and obtain a JWT token.
- `POST /api/auth/login` – Login with email & password.
- `GET /api/auth/profile` – Fetch current user profile.

### Bill Management APIs
- `POST /api/bills/upload` – Upload medical bill PDF/Image.
- `GET /api/bills/` – List all uploaded bills for the user.
- `GET /api/bills/{bill_id}` – View bill details.
- `DELETE /api/bills/{bill_id}` – Delete bill and records.

### OCR & Extraction APIs
- `POST /api/ocr/extract/{bill_id}` – Extract tabular medicine lines, strengths, quantities, rates.
- `GET /api/ocr/results/{bill_id}` – Retrieve extracted items.
- `PUT /api/ocr/items/{item_id}` – Manually correct extracted spelling, strength, quantity, or rate.

### Medicine & Matching APIs
- `GET /api/medicines/search?q={query}` – Search official medicine registry by brand or generic.
- `GET /api/medicines/match?q={query}` – Test RapidFuzz matching + strength verification.
- `GET /api/medicines/{medicine_id}` – Get medicine metadata and brand aliases.
- `GET /api/medicines/{medicine_id}/prices` – Get official regulatory price notifications for a medicine.

### Pricing & Audit APIs
- `POST /api/audit/{bill_id}` – Execute deterministic NPPA audit on all extracted bill items.
- `GET /api/audit/{audit_id}` – Get audit summary metrics (flagged count, total discrepancy).
- `GET /api/audit/{audit_id}/results` – Get item-by-item discrepancy calculations with legal references.
- `GET /api/pricing/check?medicine_name={name}&billed_unit_price={price}&quantity={qty}` – Real-time standalone rate check.

### Report APIs
- `POST /api/reports/generate/{audit_id}` – Generate ReportLab PDF grievance report.
- `GET /api/reports/{report_id}` – Download the generated PDF.

---

## 6. Testing

Run the full automated test suite with Pytest:
```bash
python -m pytest app/tests/ -v
```

Run the end-to-end simulation script:
```bash
python scripts/run_audit_cli.py
```
This script uploads `sample_hospital_bill.pdf`, runs OCR extraction, matches medicines with RapidFuzz, calculates discrepancies with the deterministic pricing engine, and compiles `generated_reports/FairMed_Audit_Report_*.pdf`.
