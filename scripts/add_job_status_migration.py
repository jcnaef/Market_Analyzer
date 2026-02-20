#!/usr/bin/env python3
"""
One-time migration script to add status and last_seen_at columns to the jobs table.
Safe to run multiple times - checks if columns exist before adding.
"""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def add_job_status_columns(db_path: str = None):
    if db_path is None:
        db_path = str(ROOT_DIR / "data" / "market_analyzer.db")
    """Add status and last_seen_at columns to jobs table if they don't exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"Connecting to {db_path}...")

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        columns_to_add = []
        if "status" not in columns:
            columns_to_add.append(("status", "TEXT DEFAULT 'open'"))
        if "last_seen_at" not in columns:
            columns_to_add.append(("last_seen_at", "TIMESTAMP"))

        if not columns_to_add:
            print("✓ All required columns already exist. No migration needed.")
            conn.close()
            return True

        # Add missing columns
        for col_name, col_def in columns_to_add:
            print(f"Adding column: {col_name} ({col_def})")
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")

        conn.commit()
        print("\n✓ Migration successful!")
        print(f"Added {len(columns_to_add)} column(s) to jobs table")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    db_path = ROOT_DIR / "data" / "market_analyzer.db"
    if not db_path.exists():
        print(f"✗ Error: {db_path} not found")
        exit(1)

    success = add_job_status_columns(str(db_path))
    exit(0 if success else 1)
