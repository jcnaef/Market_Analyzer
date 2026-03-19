"""Run database migrations in order, inside transactions.

Usage:
    python scripts/run_migrations.py                   # uses DATABASE_URL from .env
    python scripts/run_migrations.py <database_url>    # uses explicit URL
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def run_migrations(db_url: str):
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Ensure migrations tracking table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            filename TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Get already-applied migrations
    cur.execute("SELECT filename FROM migrations")
    applied = {row[0] for row in cur.fetchall()}

    # Find and sort migration files
    migration_files = sorted(
        f for f in MIGRATIONS_DIR.iterdir()
        if f.suffix == ".sql" and f.name not in applied
    )

    if not migration_files:
        print("No new migrations to apply.")
        conn.close()
        return

    conn.close()

    # Apply each migration inside its own transaction
    for migration_file in migration_files:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cur = conn.cursor()

        sql = migration_file.read_text()
        print(f"Applying {migration_file.name}...", end=" ")

        try:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO migrations (filename) VALUES (%s)",
                (migration_file.name,),
            )
            conn.commit()
            print("OK")
        except Exception as e:
            conn.rollback()
            print(f"FAILED\n  Error: {e}")
            conn.close()
            sys.exit(1)
        finally:
            conn.close()

    print("All migrations applied.")


if __name__ == "__main__":
    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv("DATABASE_URL", "postgresql:///market_analyzer?host=/var/run/postgresql")
    )
    run_migrations(url)
