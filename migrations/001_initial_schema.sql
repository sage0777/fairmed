-- ====================================================================
-- FAIRMED DATABASE SCHEMA: PostgreSQL / Supabase
-- Initial Migration: 001_initial_schema.sql
-- ====================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. MEDICINES TABLE
CREATE TABLE IF NOT EXISTS medicines (
    id VARCHAR(36) PRIMARY KEY,
    generic_name VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255),
    active_ingredients TEXT NOT NULL,
    strength VARCHAR(100) NOT NULL,
    dosage_form VARCHAR(100) NOT NULL,
    route VARCHAR(100),
    pack_size VARCHAR(100),
    manufacturer VARCHAR(255),
    category VARCHAR(100) DEFAULT 'SCHEDULED', -- SCHEDULED, NON_SCHEDULED, ONCOLOGY, ETC.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_medicines_generic_name ON medicines(generic_name);
CREATE INDEX IF NOT EXISTS idx_medicines_brand_name ON medicines(brand_name);
CREATE INDEX IF NOT EXISTS idx_medicines_strength ON medicines(strength);

-- 3. MEDICINE ALIASES TABLE
CREATE TABLE IF NOT EXISTS medicine_aliases (
    id VARCHAR(36) PRIMARY KEY,
    medicine_id VARCHAR(36) NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    alias_name VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) NOT NULL DEFAULT 'BRAND' -- BRAND, GENERIC, SPELLING_VARIANT
);
CREATE INDEX IF NOT EXISTS idx_aliases_medicine_id ON medicine_aliases(medicine_id);
CREATE INDEX IF NOT EXISTS idx_aliases_name ON medicine_aliases(alias_name);

-- 4. SOURCE DOCUMENTS TABLE
CREATE TABLE IF NOT EXISTS source_documents (
    id VARCHAR(36) PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    issuing_authority VARCHAR(255) DEFAULT 'NPPA, Ministry of Chemicals and Fertilizers',
    notification_number VARCHAR(100) NOT NULL,
    publication_date DATE,
    effective_date DATE NOT NULL,
    document_url TEXT,
    file_hash VARCHAR(128),
    verification_status VARCHAR(50) DEFAULT 'VERIFIED' -- VERIFIED, PROVISIONAL, PENDING_REVIEW
);
CREATE INDEX IF NOT EXISTS idx_source_docs_notif ON source_documents(notification_number);

-- 5. PRICING RECORDS TABLE
CREATE TABLE IF NOT EXISTS pricing_records (
    id VARCHAR(36) PRIMARY KEY,
    medicine_id VARCHAR(36) NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    pricing_category VARCHAR(100) NOT NULL, -- DPCO_SCHEDULED_CEILING, TRADE_MARGIN_CAPPED, NOTIFIED_MRP, NON_SCHEDULED
    price_type VARCHAR(50) NOT NULL DEFAULT 'CEILING_PRICE', -- CEILING_PRICE, NOTIFIED_MRP, RETAIL_PRICE
    ceiling_price NUMERIC(12, 4),
    notified_mrp NUMERIC(12, 4),
    unit VARCHAR(100) NOT NULL, -- 1 Tablet, 1 Capsule, 1 Ampoule, 100ml, etc.
    pack_size VARCHAR(100),
    effective_from DATE NOT NULL,
    effective_to DATE,
    notification_number VARCHAR(100) NOT NULL,
    source_document VARCHAR(255) NOT NULL,
    source_page INT,
    verification_status VARCHAR(50) DEFAULT 'OFFICIAL_VERIFIED', -- OFFICIAL_VERIFIED, PROVISIONAL, UNVERIFIED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pricing_medicine_id ON pricing_records(medicine_id);
CREATE INDEX IF NOT EXISTS idx_pricing_effective_dates ON pricing_records(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_pricing_category ON pricing_records(pricing_category);

-- 6. BILLS TABLE
CREATE TABLE IF NOT EXISTS bills (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    bill_date DATE,
    hospital_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'UPLOADED' -- UPLOADED, OCR_EXTRACTED, AUDITED, FAILED
);
CREATE INDEX IF NOT EXISTS idx_bills_user_id ON bills(user_id);
CREATE INDEX IF NOT EXISTS idx_bills_date ON bills(bill_date);

-- 7. EXTRACTED ITEMS TABLE
CREATE TABLE IF NOT EXISTS extracted_items (
    id VARCHAR(36) PRIMARY KEY,
    bill_id VARCHAR(36) NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    extracted_medicine_name VARCHAR(255) NOT NULL,
    extracted_strength VARCHAR(100),
    dosage_form VARCHAR(100),
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1.00,
    billed_unit_price NUMERIC(12, 4) NOT NULL,
    billed_total NUMERIC(12, 4) NOT NULL,
    matched_medicine_id VARCHAR(36) REFERENCES medicines(id) ON DELETE SET NULL,
    confidence_score NUMERIC(5, 2) DEFAULT 0.00,
    verification_status VARCHAR(50) DEFAULT 'PENDING_MATCH' -- PENDING_MATCH, MATCHED, UNMATCHED, UNCERTAIN
);
CREATE INDEX IF NOT EXISTS idx_extracted_items_bill_id ON extracted_items(bill_id);
CREATE INDEX IF NOT EXISTS idx_extracted_matched_medicine ON extracted_items(matched_medicine_id);

-- 8. AUDITS TABLE
CREATE TABLE IF NOT EXISTS audits (
    id VARCHAR(36) PRIMARY KEY,
    bill_id VARCHAR(36) NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    audit_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    total_items INT DEFAULT 0,
    verified_items INT DEFAULT 0,
    flagged_items INT DEFAULT 0,
    total_potential_difference NUMERIC(12, 4) DEFAULT 0.00,
    audit_status VARCHAR(50) DEFAULT 'COMPLETED' -- IN_PROGRESS, COMPLETED, FAILED
);
CREATE INDEX IF NOT EXISTS idx_audits_bill_id ON audits(bill_id);

-- 9. AUDIT RESULTS TABLE
CREATE TABLE IF NOT EXISTS audit_results (
    id VARCHAR(36) PRIMARY KEY,
    audit_id VARCHAR(36) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    extracted_item_id VARCHAR(36) NOT NULL REFERENCES extracted_items(id) ON DELETE CASCADE,
    pricing_record_id VARCHAR(36) REFERENCES pricing_records(id) ON DELETE SET NULL,
    billed_price NUMERIC(12, 4) NOT NULL,
    reference_price NUMERIC(12, 4),
    price_difference NUMERIC(12, 4) DEFAULT 0.00,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1.00,
    total_difference NUMERIC(12, 4) DEFAULT 0.00,
    result_status VARCHAR(50) NOT NULL, -- COMPLIANT, OVERCHARGED, NO_CEILING_APPLICABLE, INSUFFICIENT_DATA
    explanation TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_results_audit_id ON audit_results(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_results_pricing_id ON audit_results(pricing_record_id);
