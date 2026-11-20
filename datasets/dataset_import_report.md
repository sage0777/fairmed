# Official NPPA Dataset Ingestion & Validation Report

**Execution Timestamp:** 1795105599.5062952
**Target Database:** sqlite:///./fairmed.db

## Summary of Ingested Datasets

| File Name | Processed | Medicines Created | Aliases Created | Pricing Records | Superseded | Duplicates Skipped |
|---|---|---|---|---|---|---|
| `dpco_nlem_scheduled_ceiling_prices.json` | 14 | 14 | 62 | 14 | 0 | 0 |
| `oncology_trade_margin_capped.json` | 2 | 2 | 6 | 2 | 0 | 0 |

## Overall Ingestion Metrics
- **Total JSON Source Files Processed:** 2
- **Total Medicine Records Processed:** 16
- **Unique Medicines Created:** 16
- **Brand Aliases Linked:** 68
- **Official Regulatory Pricing Records Inserted:** 16
- **Historical Superseded Records Handled:** 0
- **Duplicates Skipped:** 0

## Data Integrity & Verification Standards
- All pricing records are verified against official Gazette Notifications (S.O. 1499(E), S.O. 1533(E), S.O. 1041(E)).
- Strengths and formulation dosage forms have been standardized.
- Units have been mapped to single-dose equivalents (1 Tablet, 1 Capsule, 1 Injection, etc.).
- Source documents and notification numbers are linked for 100% legal traceability.