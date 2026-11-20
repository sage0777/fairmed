-- ====================================================================
-- FAIRMED SUPABASE ROW LEVEL SECURITY (RLS) POLICIES
-- Migration: 002_rls_policies.sql
-- ====================================================================

-- 1. Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE medicines ENABLE ROW LEVEL SECURITY;
ALTER TABLE medicine_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_results ENABLE ROW LEVEL SECURITY;

-- 2. PUBLIC READ POLICIES FOR REGULATORY MASTER DATA
-- Regulatory datasets are publicly readable by all authenticated and anonymous clients
CREATE POLICY "Public read access for medicines"
ON medicines FOR SELECT USING (true);

CREATE POLICY "Public read access for medicine_aliases"
ON medicine_aliases FOR SELECT USING (true);

CREATE POLICY "Public read access for source_documents"
ON source_documents FOR SELECT USING (true);

CREATE POLICY "Public read access for pricing_records"
ON pricing_records FOR SELECT USING (true);

-- 3. USER POLICIES FOR USER ACCOUNTS
CREATE POLICY "Users can read own profile"
ON users FOR SELECT
USING (auth.uid()::text = id OR auth.jwt() ->> 'sub' = id);

CREATE POLICY "Users can update own profile"
ON users FOR UPDATE
USING (auth.uid()::text = id OR auth.jwt() ->> 'sub' = id);

-- 4. BILLS POLICIES (Users can only access their own bills)
CREATE POLICY "Users can view own bills"
ON bills FOR SELECT
USING (auth.uid()::text = user_id OR auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users can insert own bills"
ON bills FOR INSERT
WITH CHECK (auth.uid()::text = user_id OR auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users can update own bills"
ON bills FOR UPDATE
USING (auth.uid()::text = user_id OR auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users can delete own bills"
ON bills FOR DELETE
USING (auth.uid()::text = user_id OR auth.jwt() ->> 'sub' = user_id);

-- 5. EXTRACTED ITEMS POLICIES (Scoped through parent bill ownership)
CREATE POLICY "Users can view own extracted items"
ON extracted_items FOR SELECT
USING (EXISTS (
    SELECT 1 FROM bills
    WHERE bills.id = extracted_items.bill_id
    AND (bills.user_id = auth.uid()::text OR bills.user_id = auth.jwt() ->> 'sub')
));

CREATE POLICY "Users can update own extracted items"
ON extracted_items FOR UPDATE
USING (EXISTS (
    SELECT 1 FROM bills
    WHERE bills.id = extracted_items.bill_id
    AND (bills.user_id = auth.uid()::text OR bills.user_id = auth.jwt() ->> 'sub')
));

-- 6. AUDITS POLICIES (Scoped through parent bill ownership)
CREATE POLICY "Users can view own audits"
ON audits FOR SELECT
USING (EXISTS (
    SELECT 1 FROM bills
    WHERE bills.id = audits.bill_id
    AND (bills.user_id = auth.uid()::text OR bills.user_id = auth.jwt() ->> 'sub')
));

-- 7. AUDIT RESULTS POLICIES (Scoped through parent audit & bill ownership)
CREATE POLICY "Users can view own audit results"
ON audit_results FOR SELECT
USING (EXISTS (
    SELECT 1 FROM audits
    JOIN bills ON bills.id = audits.bill_id
    WHERE audits.id = audit_results.audit_id
    AND (bills.user_id = auth.uid()::text OR bills.user_id = auth.jwt() ->> 'sub')
));
