#!/usr/bin/env python3
"""Collect Google Jobs listings from the most populous city in each US state."""

import argparse
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so market_analyzer is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_analyzer.collector import (
    TOP_CITIES_BY_STATE,
    get_google_jobs,
    save_google_jobs_to_db,
)


def main():
    parser = argparse.ArgumentParser(
        description="Collect Google Jobs listings across US states."
    )
    parser.add_argument(
        "--query", default="software developer", help="Job search query (default: 'software developer')"
    )
    parser.add_argument(
        "--pages", type=int, default=10, help="Number of result pages per city (default: 10)"
    )
    parser.add_argument(
        "--states", default=None,
        help="Comma-separated list of state names to collect (default: all 50)"
    )
    parser.add_argument(
        "--delay", type=float, default=2,
        help="Seconds to wait between cities (default: 2)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and print counts but don't save to DB"
    )
    args = parser.parse_args()

    # Determine which states to process
    if args.states:
        requested = [s.strip() for s in args.states.split(",")]
        cities = {}
        for state in requested:
            if state not in TOP_CITIES_BY_STATE:
                print(f"Warning: '{state}' not found in TOP_CITIES_BY_STATE, skipping.")
            else:
                cities[state] = TOP_CITIES_BY_STATE[state]
        if not cities:
            print("Error: no valid states specified.")
            sys.exit(1)
    else:
        cities = TOP_CITIES_BY_STATE

    total_jobs = 0
    total_states = len(cities)

    print(f"\nCollecting Google Jobs from {total_states} state(s)")
    print(f"Query: '{args.query}' | Pages per city: {args.pages} | Dry run: {args.dry_run}")
    print("=" * 60)

    for i, (state, city) in enumerate(cities.items(), 1):
        print(f"\n[{i}/{total_states}] {state} ({city})")

        try:
            jobs = get_google_jobs(query=args.query, location=city, num_pages=args.pages)
            total_jobs += len(jobs)
            print(f"  -> {len(jobs)} jobs collected")

            if not args.dry_run and jobs:
                save_google_jobs_to_db(jobs)

        except Exception as e:
            print(f"  Error: {e}")

        if i < total_states:
            time.sleep(args.delay)

    print("\n" + "=" * 60)
    print(f"Done. {total_jobs} total jobs collected from {total_states} state(s).")
    if args.dry_run:
        print("(Dry run — nothing saved to DB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
