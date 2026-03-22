"""
GDPR-Compliant Data Cleanup Utility
====================================

This script securely deletes all personal data from the priAge system
while preserving only the encrypted verification tokens.

GDPR Compliance:
- Article 5(1)(e) - Storage Limitation
- Article 17 - Right to Erasure
- Article 5(1)(f) - Integrity and Confidentiality

Usage:
    python gdpr_data_cleanup.py [--dry-run] [--all] [--older-than DAYS]

Options:
    --dry-run           Show what would be deleted without actually deleting
    --all               Delete all personal data (snapshots, holograms, facial data)
    --older-than DAYS   Only delete data older than N days
    --keep-tokens       Keep verification tokens (default: True)
    --verify            Verify deletion with cryptographic proof

Examples:
    # Dry run to see what would be deleted
    python gdpr_data_cleanup.py --dry-run --all

    # Delete all personal data older than 1 day
    python gdpr_data_cleanup.py --all --older-than 1

    # Delete everything with verification
    python gdpr_data_cleanup.py --all --verify

"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
from secure_deletion import GDPRCompliantDataEraser, DeletionResult


# ============================================================================
# GDPR DATA CATEGORIES - What data is stored and where
# ============================================================================

DATA_CATEGORIES = {
    "id_snapshots": {
        "path": "outputs/snapshot_*",
        "description": "ID card snapshots (photo, DOB, name, ID number)",
        "gdpr_category": "Personal Identifiable Information (PII)",
        "sensitivity": "HIGH",
        "legal_basis": "Article 6(1)(a) - Consent for age verification",
    },
    "hologram_detection": {
        "path": "outputs/hologram_*",
        "description": "Hologram detection images (ID card images)",
        "gdpr_category": "Personal Identifiable Information (PII)",
        "sensitivity": "HIGH",
        "legal_basis": "Article 6(1)(a) - Consent for authenticity check",
    },
    "facial_recognition": {
        "path": "outputs/facial_recognition/*",
        "description": "Facial comparison images (biometric data)",
        "gdpr_category": "Special Category Data - Biometric (Article 9)",
        "sensitivity": "CRITICAL",
        "legal_basis": "Article 9(2)(a) - Explicit consent for biometric processing",
    },
    "tokens": {
        "path": "outputs/tokens/*",
        "description": "Encrypted verification tokens (only is_adult boolean)",
        "gdpr_category": "Minimized Data (GDPR-compliant)",
        "sensitivity": "LOW",
        "legal_basis": "Article 6(1)(a) - Necessary for verification purpose",
    },
    "logs": {
        "path": "outputs/logs/*",
        "description": "System logs (may contain timestamps, no PII)",
        "gdpr_category": "Operational Data",
        "sensitivity": "LOW",
        "legal_basis": "Article 6(1)(f) - Legitimate interest (security)",
    },
}


# ============================================================================
# Logging Configuration
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for GDPR cleanup operations"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'gdpr_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

    logger = logging.getLogger(__name__)
    return logger


# ============================================================================
# Data Discovery
# ============================================================================

def discover_personal_data(older_than_days: int = None) -> List[Tuple[str, Path]]:
    """
    Discover all personal data files in the system.

    Args:
        older_than_days: Only return files older than N days (None = all files)

    Returns:
        List of (category_name, file_path) tuples
    """
    discovered = []
    cutoff_time = None

    if older_than_days is not None:
        cutoff_time = datetime.now() - timedelta(days=older_than_days)

    for category, info in DATA_CATEGORIES.items():
        # Skip tokens if we want to keep them
        if category == "tokens":
            continue

        # Find all matching paths
        for pattern in info["path"].split(","):
            pattern = pattern.strip()
            base_path = Path(".")

            # Handle glob patterns
            if "*" in pattern:
                matches = list(base_path.glob(pattern))
            else:
                matches = [Path(pattern)] if Path(pattern).exists() else []

            for path in matches:
                # Check age if specified
                if cutoff_time:
                    file_time = datetime.fromtimestamp(path.stat().st_mtime)
                    if file_time > cutoff_time:
                        continue

                discovered.append((category, path))

    return discovered


# ============================================================================
# Deletion Operations
# ============================================================================

def delete_personal_data(
    files: List[Tuple[str, Path]],
    dry_run: bool = False,
    verify: bool = False,
    logger: logging.Logger = None
) -> Tuple[int, int, int]:
    """
    Securely delete personal data using DoD 5220.22-M standard.

    Args:
        files: List of (category, path) tuples to delete
        dry_run: If True, only simulate deletion
        verify: If True, verify deletion cryptographically
        logger: Logger instance

    Returns:
        Tuple of (successful_deletions, failed_deletions, total_bytes_deleted)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    eraser = GDPRCompliantDataEraser()
    successful = 0
    failed = 0
    total_bytes = 0

    logger.info("="*70)
    logger.info("GDPR-COMPLIANT SECURE DELETION - DoD 5220.22-M")
    logger.info("="*70)

    for category, path in files:
        category_info = DATA_CATEGORIES.get(category, {})
        sensitivity = category_info.get("sensitivity", "UNKNOWN")

        logger.info(f"\n{category.upper()}: {path}")
        logger.info(f"  Sensitivity: {sensitivity}")
        logger.info(f"  GDPR Category: {category_info.get('gdpr_category', 'Unknown')}")

        if dry_run:
            logger.info("  [DRY RUN] Would delete with DoD 5220.22-M (3-pass overwrite)")
            successful += 1
            continue

        # Perform actual deletion
        if path.is_file():
            result = eraser.erase_file(path, verify=verify)
        elif path.is_dir():
            result = eraser.erase_directory(path, verify=verify)
        else:
            logger.warning(f"  Skipping: Path does not exist")
            failed += 1
            continue

        # Log result
        if result.success:
            logger.info(f"  ✓ DELETED: {result.files_deleted} files, {result.bytes_overwritten} bytes")
            successful += 1
            total_bytes += result.bytes_overwritten
        else:
            logger.error(f"  ✗ FAILED: {result.error_message}")
            failed += 1

    logger.info("\n" + "="*70)
    logger.info("DELETION SUMMARY")
    logger.info("="*70)
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total bytes overwritten: {total_bytes:,}")
    logger.info(f"Method: DoD 5220.22-M (3-pass: zeros → ones → random)")
    logger.info(f"Data recovery: {'IMPOSSIBLE' if successful > 0 else 'N/A'}")
    logger.info("="*70)

    return successful, failed, total_bytes


# ============================================================================
# GDPR Compliance Report
# ============================================================================

def generate_compliance_report(
    discovered: List[Tuple[str, Path]],
    deleted: int,
    failed: int,
    total_bytes: int,
    dry_run: bool = False
) -> str:
    """
    Generate a GDPR compliance report for audit purposes.

    Returns:
        Formatted compliance report as string
    """
    report = []
    report.append("="*70)
    report.append("GDPR COMPLIANCE REPORT - STORAGE LIMITATION (Article 5(1)(e))")
    report.append("="*70)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Mode: {'DRY RUN' if dry_run else 'ACTUAL DELETION'}")
    report.append("\n" + "-"*70)
    report.append("DATA DISCOVERED:")
    report.append("-"*70)

    # Group by category
    by_category = {}
    for category, path in discovered:
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(path)

    for category, paths in by_category.items():
        info = DATA_CATEGORIES.get(category, {})
        report.append(f"\n{category.upper()}:")
        report.append(f"  Description: {info.get('description', 'N/A')}")
        report.append(f"  GDPR Category: {info.get('gdpr_category', 'N/A')}")
        report.append(f"  Sensitivity: {info.get('sensitivity', 'N/A')}")
        report.append(f"  Items found: {len(paths)}")

    report.append("\n" + "-"*70)
    report.append("DELETION RESULTS:")
    report.append("-"*70)
    report.append(f"Items discovered: {len(discovered)}")
    report.append(f"Successfully deleted: {deleted}")
    report.append(f"Failed to delete: {failed}")
    report.append(f"Total bytes overwritten: {total_bytes:,}")
    report.append(f"Deletion standard: DoD 5220.22-M (3-pass overwrite)")

    report.append("\n" + "-"*70)
    report.append("GDPR COMPLIANCE STATUS:")
    report.append("-"*70)

    if not dry_run and deleted > 0 and failed == 0:
        report.append("✓ COMPLIANT - All personal data securely deleted")
        report.append("✓ Article 5(1)(e) - Storage Limitation: ACHIEVED")
        report.append("✓ Data recovery: IMPOSSIBLE (DoD standard)")
    elif not dry_run and failed > 0:
        report.append("⚠ PARTIAL COMPLIANCE - Some deletions failed")
        report.append("⚠ Manual review required for failed items")
    else:
        report.append("ℹ DRY RUN - No actual deletion performed")

    report.append("\n" + "="*70)

    return "\n".join(report)


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main entry point for GDPR data cleanup utility"""
    parser = argparse.ArgumentParser(
        description="GDPR-compliant secure deletion of personal data from priAge system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all personal data (snapshots, holograms, facial data)"
    )

    parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Only delete data older than N days"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify deletion with cryptographic proof (slower but more secure)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(verbose=args.verbose)

    logger.info("="*70)
    logger.info("GDPR DATA CLEANUP UTILITY - priAge System")
    logger.info("="*70)

    # Discover personal data
    logger.info("\nPhase 1: Discovering personal data...")
    discovered = discover_personal_data(older_than_days=args.older_than)

    if not discovered:
        logger.info("No personal data found to delete.")
        return 0

    logger.info(f"Found {len(discovered)} items containing personal data")

    # Display what will be deleted
    logger.info("\nData to be deleted:")
    for category, path in discovered:
        logger.info(f"  - [{category}] {path}")

    # Confirm deletion (unless dry-run)
    if not args.dry_run:
        logger.warning("\n⚠ WARNING: This will PERMANENTLY DELETE all listed data!")
        logger.warning("⚠ Data will be overwritten 3 times (DoD 5220.22-M)")
        logger.warning("⚠ Recovery will be IMPOSSIBLE, even with forensic tools!")

        response = input("\nType 'DELETE' to confirm deletion: ")
        if response != "DELETE":
            logger.info("Deletion cancelled by user")
            return 1

    # Perform deletion
    logger.info("\nPhase 2: Secure deletion...")
    successful, failed, total_bytes = delete_personal_data(
        discovered,
        dry_run=args.dry_run,
        verify=args.verify,
        logger=logger
    )

    # Generate compliance report
    logger.info("\nPhase 3: Generating compliance report...")
    report = generate_compliance_report(discovered, successful, failed, total_bytes, args.dry_run)
    print("\n" + report)

    # Save report to file
    report_file = f"gdpr_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    logger.info(f"\nCompliance report saved to: {report_file}")

    # Return exit code
    if failed > 0:
        logger.error("\nSome deletions failed. Please review manually.")
        return 1

    logger.info("\nGDPR data cleanup completed successfully!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)
