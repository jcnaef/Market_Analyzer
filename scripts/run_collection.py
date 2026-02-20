#!/usr/bin/env python3
"""
Orchestrator script for automated daily job collection pipeline.
Runs the full data collection, processing, and database migration in sequence.

Usage:
  python run_collection.py              # Full pipeline with API calls
  python run_collection.py --skip-api   # Skip API calls, process existing muse_jobs.json

Can be scheduled as a cron job:
  0 2 * * * /path/to/venv/bin/python /path/to/run_collection.py >> /path/to/collection.log 2>&1
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src and scripts to path for imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from market_analyzer.collector import collect_all_states, save_to_file
from market_analyzer.cleaner import process_dataset
from migrate_to_sqlite import DatabaseMigrator


def run_collection(skip_api=False):
    """Run the complete collection pipeline."""
    start_time = datetime.now()
    print("\n" + "="*70)
    print("🚀 Market Analyzer - Automated Job Collection Pipeline")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if skip_api:
        print("Mode: Processing existing data (API calls skipped)")
    print("="*70 + "\n")

    try:
        jobs = None

        if not skip_api:
            # Step 1: Collect jobs from all states
            print("📡 STEP 1: Collecting jobs from all US states...")
            print("-" * 70)
            jobs = collect_all_states(category="Software Engineering", page_limit=20)
            if not jobs:
                print("✗ No jobs collected. Aborting pipeline.")
                return False

            # Step 2: Save to muse_jobs.json
            print("\n💾 STEP 2: Saving raw job data...")
            print("-" * 70)
            save_to_file(jobs, filename="muse_jobs.json")
        else:
            # Verify muse_jobs.json exists
            muse_file = ROOT_DIR / "data" / "muse_jobs.json"
            if not muse_file.exists():
                print("✗ muse_jobs.json not found. Cannot skip API calls without existing data.")
                return False
            print("📂 STEP 1: Using existing muse_jobs.json (API calls skipped)")
            print("-" * 70)

        # Step 3: Process with AI data cleaner
        print("\n🧠 STEP 2: Processing jobs with NLP (skill extraction)..." if skip_api else "\n🧠 STEP 3: Processing jobs with NLP (skill extraction)...")
        print("-" * 70)
        process_dataset("muse_jobs.json", skills_file="skills.json")

        # Step 4: Migrate to database
        print("\n🗄️  STEP 3: Upserting to SQLite database..." if skip_api else "\n🗄️  STEP 4: Upserting to SQLite database...")
        print("-" * 70)
        migrator = DatabaseMigrator(
            db_path=str(ROOT_DIR / "data" / "market_analyzer.db"),
            csv_path=str(ROOT_DIR / "data" / "processed_jobs.csv")
        )
        migrator.migrate()

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*70)
        print("✓ COLLECTION PIPELINE COMPLETE")
        print("="*70)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📊 Summary:")
        if not skip_api:
            print(f"  • Jobs collected:    {len(jobs)}")
        print(f"  • Jobs imported:     {migrator.stats.get('jobs_imported', 0)}")
        print(f"  • Jobs updated:      {migrator.stats.get('jobs_updated', 0)}")
        print(f"  • Jobs closed:       {migrator.stats.get('jobs_closed', 0)}")
        print(f"  • Errors:            {migrator.stats.get('errors', 0)}")
        print("="*70 + "\n")

        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n✗ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job collection pipeline orchestrator")
    parser.add_argument("--skip-api", action="store_true", help="Skip API calls and process existing muse_jobs.json")
    args = parser.parse_args()

    success = run_collection(skip_api=args.skip_api)
    sys.exit(0 if success else 1)
