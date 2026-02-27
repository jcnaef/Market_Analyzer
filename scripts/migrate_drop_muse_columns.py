#!/usr/bin/env python3
"""Migration: Remove muse_company_id, muse_job_id, and clean_description columns.

Copies clean_description into description, then rebuilds tables without the
removed columns. Creates a backup before making changes.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_analyzer.db"
BACKUP_PATH = DB_PATH.with_suffix(f".backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")


def migrate():
    # Backup
    print(f"Backing up database to {BACKUP_PATH.name}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"  Done.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = OFF")

    print("Migrating companies table (dropping muse_company_id)...")
    conn.executescript("""
        CREATE TABLE companies_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            short_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO companies_new (id, name, short_name, created_at, updated_at)
            SELECT id, name, short_name, created_at, updated_at FROM companies;

        DROP TABLE companies;
        ALTER TABLE companies_new RENAME TO companies;

        CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
    """)

    print("Migrating jobs table (dropping muse_job_id, merging clean_description into description)...")
    conn.executescript("""
        CREATE TABLE jobs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company_id INTEGER NOT NULL,
            description TEXT,
            salary_min DECIMAL(10, 2),
            salary_max DECIMAL(10, 2),
            currency TEXT DEFAULT 'USD',
            is_remote BOOLEAN DEFAULT 0,
            job_level TEXT,
            publication_date TIMESTAMP,
            job_url TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );

        INSERT INTO jobs_new (id, title, company_id, description, salary_min, salary_max,
                              currency, is_remote, job_level, publication_date, job_url,
                              fetched_at, last_seen_at, status, created_at, updated_at)
            SELECT id, title, company_id,
                   COALESCE(clean_description, description),
                   salary_min, salary_max, currency, is_remote, job_level,
                   publication_date, job_url, fetched_at, last_seen_at, status,
                   created_at, updated_at
            FROM jobs;

        DROP TABLE jobs;
        ALTER TABLE jobs_new RENAME TO jobs;

        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_publication_date ON jobs(publication_date);
        CREATE INDEX IF NOT EXISTS idx_jobs_remote ON jobs(is_remote);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_last_seen_at ON jobs(last_seen_at);
    """)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
