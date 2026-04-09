#!/usr/bin/env python3
"""
Master cron orchestrator for job data collection.

Manages API budgets across SerpAPI and Muse, rotates states to maximize
coverage within rate limits, and runs cleaning/aggregation.

API Limits:
  SerpAPI:  1,000 searches/month, 200 searches/hour
  Muse:     250 searches/month

Schedule (via crontab):
  # Daily at 2 AM — SerpAPI collection (25 states, rotated daily)
  0 2 * * * /path/to/venv/bin/python /path/to/cron_collect.py serp >> /path/to/logs/serp.log 2>&1

  # Weekly on Sunday at 3 AM — Muse collection (all 50 states, 1 page each)
  0 3 * * 0 /path/to/venv/bin/python /path/to/cron_collect.py muse >> /path/to/logs/muse.log 2>&1

Usage:
  python cron_collect.py serp              # SerpAPI daily rotation (25 states)
  python cron_collect.py serp --pages 2    # 2 pages per state (50 calls)
  python cron_collect.py muse              # Muse weekly (50 states x 1 page)
  python cron_collect.py muse --pages 2    # 2 pages per state (100 calls)
  python cron_collect.py all               # Run serp + muse in sequence
  python cron_collect.py status            # Show API usage and rotation state
  python cron_collect.py --dry-run serp    # Preview without API calls or DB writes
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

STATE_FILE = ROOT_DIR / "data" / "cron_state.json"
LOG_DIR = ROOT_DIR / "logs"

SERP_DELAY_BETWEEN_STATES = 3  # stays well under 200/hr
MUSE_DELAY_BETWEEN_STATES = 2

# Queries rotate each run for broader coverage
SEARCH_QUERIES = [
    "software developer",
    "software engineer",
    "data engineer",
    "full stack developer",
    "frontend developer",
    "backend developer",
    "devops engineer",
    "machine learning engineer",
]


def _get_collector():
    """Lazy import of collector module (requires psycopg2, serpapi, etc.)."""
    from market_analyzer.collector import (
        TOP_CITIES_BY_STATE,
        get_google_jobs,
        save_google_jobs_to_db,
        get_muse_jobs,
        save_to_file,
    )
    return TOP_CITIES_BY_STATE, get_google_jobs, save_google_jobs_to_db, get_muse_jobs, save_to_file


def _get_state_groups():
    """Build A/B state rotation groups from collector's state list."""
    TOP_CITIES_BY_STATE, *_ = _get_collector()
    all_states = list(TOP_CITIES_BY_STATE.keys())
    return all_states, all_states[:25], all_states[25:]


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "serp_group": "A",
        "serp_query_index": 0,
        "serp_monthly_calls": 0,
        "muse_monthly_calls": 0,
        "month": datetime.now().strftime("%Y-%m"),
        "last_serp_run": None,
        "last_muse_run": None,
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def reset_monthly_if_needed(state: dict) -> dict:
    current_month = datetime.now().strftime("%Y-%m")
    if state.get("month") != current_month:
        state["serp_monthly_calls"] = 0
        state["muse_monthly_calls"] = 0
        state["month"] = current_month
    return state


# ── SerpAPI collection ──────────────────────────────────────────────────────

def run_serp(pages: int = 1, dry_run: bool = False):
    TOP_CITIES_BY_STATE, get_google_jobs, save_google_jobs_to_db, _, _ = _get_collector()
    ALL_STATES, GROUP_A, GROUP_B = _get_state_groups()

    state = load_state()
    state = reset_monthly_if_needed(state)

    group_label = state.get("serp_group", "A")
    query_index = state.get("serp_query_index", 0) % len(SEARCH_QUERIES)
    query = SEARCH_QUERIES[query_index]
    states_today = list(GROUP_A if group_label == "A" else GROUP_B)
    estimated_calls = len(states_today) * pages

    print(f"\n{'='*60}")
    print(f"SerpAPI Collection — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Query:            \"{query}\" ({query_index + 1}/{len(SEARCH_QUERIES)})")
    print(f"Group:            {group_label} ({len(states_today)} states)")
    print(f"Pages per state:  {pages}")
    print(f"Estimated calls:  {estimated_calls}")
    print(f"Monthly used:     {state['serp_monthly_calls']}/1000")
    print(f"After this run:   ~{state['serp_monthly_calls'] + estimated_calls}/1000")
    print(f"Dry run:          {dry_run}")
    print(f"{'='*60}\n")

    if state["serp_monthly_calls"] + estimated_calls > 1000:
        remaining = 1000 - state["serp_monthly_calls"]
        print(f"WARNING: Would exceed monthly limit. {remaining} calls remaining.")
        if remaining <= 0:
            print("Monthly budget exhausted. Skipping SerpAPI collection.")
            return
        pages = max(1, remaining // len(states_today))
        if pages == 0:
            states_today = states_today[:remaining]
            pages = 1
        estimated_calls = len(states_today) * pages
        print(f"Adjusted: {len(states_today)} states x {pages} pages = {estimated_calls} calls\n")

    total_jobs = 0
    actual_calls = 0

    for i, state_name in enumerate(states_today, 1):
        city = TOP_CITIES_BY_STATE[state_name]
        print(f"[{i}/{len(states_today)}] {state_name} ({city})")

        if dry_run:
            print(f"  -> [DRY RUN] would fetch {pages} page(s)")
            actual_calls += pages
            continue

        try:
            jobs = get_google_jobs(
                query=query,
                location=city,
                num_pages=pages,
            )
            total_jobs += len(jobs)
            actual_calls += min(pages, max(1, len(jobs) // 10 + 1))

            if jobs:
                save_google_jobs_to_db(jobs)

        except Exception as e:
            print(f"  Error: {e}")

        if i < len(states_today):
            time.sleep(SERP_DELAY_BETWEEN_STATES)

    state["serp_monthly_calls"] += actual_calls
    state["serp_group"] = "B" if group_label == "A" else "A"
    state["serp_query_index"] = (query_index + 1) % len(SEARCH_QUERIES)
    state["last_serp_run"] = datetime.now().isoformat()
    if not dry_run:
        save_state(state)

    print(f"\n{'='*60}")
    print(f"SerpAPI Done: {total_jobs} jobs collected, ~{actual_calls} API calls used")
    print(f"Monthly total: {state['serp_monthly_calls']}/1000")
    print(f"Next run: group {state['serp_group']}, query \"{SEARCH_QUERIES[state['serp_query_index']]}\"")
    print(f"{'='*60}\n")


# ── Muse collection ────────────────────────────────────────────────────────

def run_muse(pages: int = 1, dry_run: bool = False):
    TOP_CITIES_BY_STATE, _, _, get_muse_jobs, save_to_file = _get_collector()
    from market_analyzer.cleaner import process_dataset
    ALL_STATES, _, _ = _get_state_groups()

    state = load_state()
    state = reset_monthly_if_needed(state)

    states_to_run = list(ALL_STATES)
    estimated_calls = len(states_to_run) * pages

    print(f"\n{'='*60}")
    print(f"Muse Collection — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"States:           {len(ALL_STATES)}")
    print(f"Pages per state:  {pages}")
    print(f"Estimated calls:  {estimated_calls}")
    print(f"Monthly used:     {state['muse_monthly_calls']}/250")
    print(f"After this run:   ~{state['muse_monthly_calls'] + estimated_calls}/250")
    print(f"Dry run:          {dry_run}")
    print(f"{'='*60}\n")

    if state["muse_monthly_calls"] + estimated_calls > 250:
        remaining = 250 - state["muse_monthly_calls"]
        print(f"WARNING: Would exceed monthly limit. {remaining} calls remaining.")
        if remaining <= 0:
            print("Monthly budget exhausted. Skipping Muse collection.")
            return
        pages = max(1, remaining // len(ALL_STATES))
        if pages == 0:
            states_to_run = ALL_STATES[:remaining]
            pages = 1
        else:
            states_to_run = ALL_STATES
        estimated_calls = len(states_to_run) * pages
        print(f"Adjusted: {len(states_to_run)} states x {pages} pages = {estimated_calls} calls\n")
    else:
        states_to_run = ALL_STATES

    all_jobs = []

    for i, state_name in enumerate(states_to_run, 1):
        city = TOP_CITIES_BY_STATE[state_name]
        print(f"[{i}/{len(states_to_run)}] {state_name} ({city})")

        if dry_run:
            print(f"  -> [DRY RUN] would fetch {pages} page(s)")
            continue

        try:
            jobs = get_muse_jobs(
                category="Software Engineering",
                location=city,
                page_limit=pages,
            )
            all_jobs.extend(jobs)
            print(f"  -> {len(jobs)} jobs")
        except Exception as e:
            print(f"  Error: {e}")

        if i < len(states_to_run):
            time.sleep(MUSE_DELAY_BETWEEN_STATES)

    if not dry_run and all_jobs:
        save_to_file(all_jobs, filename="muse_jobs.json")

        print("\nProcessing jobs with NLP skill extraction...")
        process_dataset("muse_jobs.json", skills_file="skills.json")

        print("Upserting to database...")
        from migrate_to_sqlite import DatabaseMigrator
        migrator = DatabaseMigrator(
            csv_path=str(ROOT_DIR / "data" / "processed_jobs.csv"),
        )
        migrator.migrate()

    actual_calls = len(states_to_run) * pages
    state["muse_monthly_calls"] += actual_calls
    state["last_muse_run"] = datetime.now().isoformat()
    if not dry_run:
        save_state(state)

    print(f"\n{'='*60}")
    print(f"Muse Done: {len(all_jobs)} jobs collected, ~{actual_calls} API calls used")
    print(f"Monthly total: {state['muse_monthly_calls']}/250")
    print(f"{'='*60}\n")


# ── Status ──────────────────────────────────────────────────────────────────

def show_status():
    state = load_state()
    state = reset_monthly_if_needed(state)

    print(f"\n{'='*60}")
    print(f"Cron Collection Status — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"\nMonth: {state['month']}")
    print(f"\nSerpAPI:")
    print(f"  Monthly usage:   {state['serp_monthly_calls']}/1000")
    print(f"  Remaining:       {1000 - state['serp_monthly_calls']}")
    print(f"  Next group:      {state.get('serp_group', 'A')}")
    qi = state.get("serp_query_index", 0) % len(SEARCH_QUERIES)
    print(f"  Next query:      \"{SEARCH_QUERIES[qi]}\" ({qi + 1}/{len(SEARCH_QUERIES)})")
    print(f"  Last run:        {state.get('last_serp_run', 'never')}")
    print(f"\nMuse:")
    print(f"  Monthly usage:   {state['muse_monthly_calls']}/250")
    print(f"  Remaining:       {250 - state['muse_monthly_calls']}")
    print(f"  Last run:        {state.get('last_muse_run', 'never')}")

    day_of_month = datetime.now().day
    if day_of_month > 1:
        serp_rate = state['serp_monthly_calls'] / day_of_month
        muse_rate = state['muse_monthly_calls'] / day_of_month
        print(f"\nProjected monthly usage:")
        print(f"  SerpAPI: ~{int(serp_rate * 30)}/1000")
        print(f"  Muse:    ~{int(muse_rate * 30)}/250")

    print(f"{'='*60}\n")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Master cron orchestrator for job data collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  serp      Run SerpAPI Google Jobs collection (daily, 25 states rotated)
  muse      Run Muse API collection (weekly, all 50 states)
  all       Run serp + muse in sequence
  status    Show API usage and rotation state
        """,
    )
    parser.add_argument("command", choices=["serp", "muse", "all", "status"])
    parser.add_argument("--pages", type=int, default=1, help="Pages per state (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls or DB writes")

    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "status":
        show_status()
    elif args.command == "serp":
        run_serp(pages=args.pages, dry_run=args.dry_run)
    elif args.command == "muse":
        run_muse(pages=args.pages, dry_run=args.dry_run)
    elif args.command == "all":
        run_serp(pages=args.pages, dry_run=args.dry_run)
        run_muse(pages=args.pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
