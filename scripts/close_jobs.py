#!/usr/bin/env python3
"""
Cron job to check stale job postings and update their status.

Pulls open jobs whose last_seen_at is older than a threshold, scrapes
each URL to see if the posting is still live, and either:
  - Updates last_seen_at to now (if the page is still up)
  - Sets status to 'closed' (if the page is gone)

Usage:
  python scripts/close_stale_jobs.py                    # default 7-day threshold
  python scripts/close_stale_jobs.py --days 14          # custom threshold
  python scripts/close_stale_jobs.py --batch-size 100   # limit per run
  python scripts/close_stale_jobs.py --dry-run           # preview without changes

Cron example (daily at 3 AM):
  0 3 * * * /path/to/venv/bin/python /path/to/close_stale_jobs.py >> /path/to/stale_jobs.log 2>&1
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql:///market_analyzer?host=/var/run/postgresql"
)

# HTTP status codes that indicate the job posting has been removed
CLOSED_STATUS_CODES = {404, 410}

# Status codes where we can't determine the job state — skip and retry next run
SKIP_STATUS_CODES = {403, 429, 503}

# Phrases in the page body that indicate the job has been taken down.
# Many sites (e.g. The Muse) return HTTP 200 but show a "not found" message.
CLOSED_PHRASES = [
    "this job is no longer available",
    "this job has been removed",
    "this job has expired",
    "this position has been filled",
    "this position is no longer available",
#    "job not found",
    "listing has expired",
    "listing not found",
    "no longer accepting applications",
    "this posting has been removed",
    "this role has been filled",
]

# Pre-compile a single regex for speed
_CLOSED_PATTERN = re.compile(
    "|".join(re.escape(phrase) for phrase in CLOSED_PHRASES),
    re.IGNORECASE,
)

REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY = 1.0   # seconds between requests to be polite


def get_stale_jobs(conn, days: int, batch_size: int) -> list[dict]:
    """Fetch open jobs not seen in the last `days` days."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, job_url, title, last_seen_at
               FROM jobs
               WHERE status = 'open'
                 AND job_url IS NOT NULL
                 AND last_seen_at < NOW() - INTERVAL '%s days'
               ORDER BY last_seen_at ASC
               LIMIT %s""",
            (days, batch_size),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def check_job_url(url: str) -> str:
    """Check if a job URL is still live.

    Returns:
        'live'    - page returned 200 and no "closed" phrases found
        'closed'  - page returned 404/410 or body contains a closed phrase
        'skip'    - couldn't determine (error, 403, 429, etc.)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; MarketAnalyzerBot/1.0; "
            "+https://github.com/jcnaef/Market_Analyzer)"
        ),
    }
    try:
        resp = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True,
        )
        print(f"Status Code: {resp.status_code}")

        if resp.status_code in CLOSED_STATUS_CODES:
            return "closed"

        if resp.status_code in SKIP_STATUS_CODES:
            return "skip"

        if resp.status_code == 200:
            # Check page content for "job removed" indicators
            match = _CLOSED_PATTERN.search(resp.text)
            if match:
                print(f"  Matched phrase: \"{match.group()}\"")
                return "closed"
            return "live"

        # Any other status — can't be sure, skip
        return "skip"

    except requests.exceptions.Timeout:
        return "skip"
    except requests.exceptions.ConnectionError:
        return "skip"
    except requests.exceptions.RequestException:
        return "skip"


def update_last_seen(conn, job_id: int):
    """Mark a job as still live by updating last_seen_at."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET last_seen_at = NOW(), updated_at = NOW() WHERE id = %s",
            (job_id,),
        )


def close_job(conn, job_id: int):
    """Mark a job as closed."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status = 'closed', updated_at = NOW() WHERE id = %s",
            (job_id,),
        )


def run(days: int = 7, batch_size: int = 500, dry_run: bool = False):
    """Main entry point."""
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"Stale Job Checker — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Threshold: {days} days | Batch: {batch_size} | Dry run: {dry_run}")
    print(f"{'='*60}\n")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        jobs = get_stale_jobs(conn, days, batch_size)
        print(f"Found {len(jobs)} stale jobs to check\n")

        if not jobs:
            conn.close()
            return

        stats = {"live": 0, "closed": 0, "skipped": 0}

        for i, job in enumerate(jobs, 1):
            job_id = job["id"]
            url = job["job_url"]
            title = (job["title"] or "Unknown")[:50]

            result = check_job_url(url)

            if result == "live":
                stats["live"] += 1
                if not dry_run:
                    update_last_seen(conn, job_id)
                print(f"  [{i}/{len(jobs)}] LIVE    — {title}\n{url}")
            elif result == "closed":
                stats["closed"] += 1
                if not dry_run:
                    close_job(conn, job_id)
                print(f"  [{i}/{len(jobs)}] CLOSED  — {title}\n{url}")
            else:
                stats["skipped"] += 1
                print(f"  [{i}/{len(jobs)}] SKIP    — {title}\n{url}")

            # Rate limiting — be polite to servers
            if i < len(jobs):
                time.sleep(REQUEST_DELAY)

        if not dry_run:
            conn.commit()
            print("\nChanges committed.")
        else:
            conn.rollback()
            print("\nDry run — no changes made.")

        elapsed = (datetime.now() - start).total_seconds()
        print(f"\n{'='*60}")
        print(f"Results: {stats['live']} live | {stats['closed']} closed | {stats['skipped']} skipped")
        print(f"Duration: {elapsed:.1f}s")
        print(f"{'='*60}\n")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check stale job postings and close dead ones"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Days since last_seen_at threshold (default: 7)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Max jobs to check per run (default: 500)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to DB",
    )
    args = parser.parse_args()

    run(days=args.days, batch_size=args.batch_size, dry_run=args.dry_run)
