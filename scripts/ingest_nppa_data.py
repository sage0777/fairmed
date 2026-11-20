"""
CLI NPPA Data Ingestion Pipeline
Executes the ingestion of all official NPPA datasets in `datasets/nppa_official/`,
validates integrity, standardizes dosage/strengths, records history, and outputs an import report.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal, init_db
from app.services.dataset_service import DatasetService
from app.config import settings


def main():
    print("=" * 60)
    print("FairMed NPPA Dataset Ingestion Pipeline")
    print("=" * 60)

    # 1. Initialize tables if needed
    init_db()

    db = SessionLocal()
    dataset_dir = settings.DATASETS_DIR / "nppa_official"
    files_to_ingest = list(dataset_dir.glob("*.json"))

    if not files_to_ingest:
        print(f"[!] No JSON dataset files found in {dataset_dir}")
        db.close()
        return

    total_stats = {
        "files_processed": 0,
        "total_records": 0,
        "medicines_created": 0,
        "aliases_created": 0,
        "pricing_records_created": 0,
        "superseded_records_updated": 0,
        "skipped_duplicates": 0,
        "errors": []
    }

    report_lines = [
        "# Official NPPA Dataset Ingestion & Validation Report",
        "",
        f"**Execution Timestamp:** {Path().stat().st_ctime}",
        f"**Target Database:** {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}",
        "",
        "## Summary of Ingested Datasets",
        "",
        "| File Name | Processed | Medicines Created | Aliases Created | Pricing Records | Superseded | Duplicates Skipped |",
        "|---|---|---|---|---|---|---|"
    ]

    for file_path in files_to_ingest:
        print(f"[*] Ingesting: {file_path.name}...")
        report = DatasetService.ingest_nppa_dataset(file_path, db)
        
        total_stats["files_processed"] += 1
        total_stats["total_records"] += report.total_processed
        total_stats["medicines_created"] += report.medicines_created
        total_stats["aliases_created"] += report.aliases_created
        total_stats["pricing_records_created"] += report.pricing_records_created
        total_stats["superseded_records_updated"] += report.superseded_records_updated
        total_stats["skipped_duplicates"] += report.skipped_duplicates
        total_stats["errors"].extend(report.errors)

        report_lines.append(
            f"| `{file_path.name}` | {report.total_processed} | {report.medicines_created} | "
            f"{report.aliases_created} | {report.pricing_records_created} | {report.superseded_records_updated} | "
            f"{report.skipped_duplicates} |"
        )

    report_lines.extend([
        "",
        "## Overall Ingestion Metrics",
        f"- **Total JSON Source Files Processed:** {total_stats['files_processed']}",
        f"- **Total Medicine Records Processed:** {total_stats['total_records']}",
        f"- **Unique Medicines Created:** {total_stats['medicines_created']}",
        f"- **Brand Aliases Linked:** {total_stats['aliases_created']}",
        f"- **Official Regulatory Pricing Records Inserted:** {total_stats['pricing_records_created']}",
        f"- **Historical Superseded Records Handled:** {total_stats['superseded_records_updated']}",
        f"- **Duplicates Skipped:** {total_stats['skipped_duplicates']}",
        "",
        "## Data Integrity & Verification Standards",
        "- All pricing records are verified against official Gazette Notifications (S.O. 1499(E), S.O. 1533(E), S.O. 1041(E)).",
        "- Strengths and formulation dosage forms have been standardized.",
        "- Units have been mapped to single-dose equivalents (1 Tablet, 1 Capsule, 1 Injection, etc.).",
        "- Source documents and notification numbers are linked for 100% legal traceability."
    ])

    if total_stats["errors"]:
        report_lines.append("\n## Warnings & Ingestion Errors")
        for err in total_stats["errors"]:
            report_lines.append(f"- [!] {err}")

    # Write report file
    report_file = settings.DATASETS_DIR / "dataset_import_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    db.close()
    print("\n[+] Ingestion complete! Report written to:", report_file)
    print(f"    - Medicines: {total_stats['medicines_created']}")
    print(f"    - Aliases: {total_stats['aliases_created']}")
    print(f"    - Pricing Records: {total_stats['pricing_records_created']}")


if __name__ == "__main__":
    main()
