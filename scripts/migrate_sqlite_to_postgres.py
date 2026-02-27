#!/usr/bin/env python3
"""Migrate data from SQLite to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py [sqlite_path] [postgres_url]

Defaults:
    sqlite_path  = data/market_analyzer.db
    postgres_url = DATABASE_URL env var or postgresql://localhost/market_analyzer
"""

import sqlite3
import sys
from pathlib import Path

import psycopg2

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
from market_analyzer.db_config import DATABASE_URL

TABLES_IN_ORDER = [
    "companies",
    "locations",
    "skill_categories",
    "skills",
    "jobs",
    "job_locations",
    "job_skills",
]


def migrate(sqlite_path: str, pg_url: str):
    # Connect to both databases
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(pg_url)
    pg_cur = pg.cursor()

    # Drop existing tables and recreate from schema.sql
    print("Dropping existing tables ...")
    for table in reversed(TABLES_IN_ORDER):
        pg_cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    pg.commit()

    schema_path = ROOT_DIR / "data" / "schema.sql"
    print(f"Creating schema from {schema_path} ...")
    with open(schema_path) as f:
        pg_cur.execute(f.read())
    pg.commit()

    # Disable FK checks during import (re-enabled at end of transaction)
    pg_cur.execute("SET session_replication_role = 'replica'")

    # Migrate each table
    for table in TABLES_IN_ORDER:
        rows = sq.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table:20} 0 rows (skipped)")
            continue

        columns = rows[0].keys()
        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        batch = []
        for row in rows:
            values = []
            for col in columns:
                val = row[col]
                # Convert SQLite 0/1 booleans for is_remote
                if col == "is_remote" and val is not None:
                    val = bool(val)
                values.append(val)
            batch.append(tuple(values))

        pg_cur.executemany(insert_sql, batch)
        pg.commit()
        print(f"  {table:20} {len(batch):>6} rows")

    # Re-enable FK checks
    pg_cur.execute("SET session_replication_role = 'origin'")
    pg.commit()

    # Clean up orphan references from SQLite (which didn't enforce FKs)
    print("\nCleaning orphan references ...")
    pg_cur.execute(
        "DELETE FROM job_locations WHERE location_id NOT IN (SELECT id FROM locations)"
    )
    print(f"  job_locations: removed {pg_cur.rowcount} orphan rows")
    pg_cur.execute(
        "DELETE FROM job_locations WHERE job_id NOT IN (SELECT id FROM jobs)"
    )
    print(f"  job_locations: removed {pg_cur.rowcount} orphan job rows")
    pg_cur.execute(
        "DELETE FROM job_skills WHERE job_id NOT IN (SELECT id FROM jobs)"
    )
    print(f"  job_skills: removed {pg_cur.rowcount} orphan job rows")
    pg_cur.execute(
        "DELETE FROM job_skills WHERE skill_id NOT IN (SELECT id FROM skills)"
    )
    print(f"  job_skills: removed {pg_cur.rowcount} orphan skill rows")
    pg.commit()

    # Reset sequences so new INSERTs get correct IDs
    print("\nResetting sequences ...")
    for table in TABLES_IN_ORDER:
        pg_cur.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = %s AND column_default LIKE 'nextval%%'",
            (table,),
        )
        seq_cols = pg_cur.fetchall()
        for (col,) in seq_cols:
            pg_cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
            )
    pg.commit()

    sq.close()
    pg.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT_DIR / "data" / "market_analyzer.db")
    pg_url = sys.argv[2] if len(sys.argv) > 2 else DATABASE_URL

    print(f"SQLite:     {sqlite_path}")
    print(f"PostgreSQL: {pg_url}")
    print()
    migrate(sqlite_path, pg_url)
