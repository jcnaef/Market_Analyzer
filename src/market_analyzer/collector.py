import requests
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from serpapi import GoogleSearch

from market_analyzer.cleaner import clean_job_text, load_skills, extract_skills_from_text
from market_analyzer.db_config import DATABASE_URL

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

MUSE_URL = "https://www.themuse.com/api/public/jobs"

# Most populous city in each US state
TOP_CITIES_BY_STATE = {
    "Alabama": "Birmingham, AL",
    "Alaska": "Anchorage, AK",
    "Arizona": "Phoenix, AZ",
    "Arkansas": "Little Rock, AR",
    "California": "Los Angeles, CA",
    "Colorado": "Denver, CO",
    "Connecticut": "Bridgeport, CT",
    "Delaware": "Wilmington, DE",
    "Florida": "Jacksonville, FL",
    "Georgia": "Atlanta, GA",
    "Hawaii": "Honolulu, HI",
    "Idaho": "Boise, ID",
    "Illinois": "Chicago, IL",
    "Indiana": "Indianapolis, IN",
    "Iowa": "Des Moines, IA",
    "Kansas": "Kansas City, KS",
    "Kentucky": "Louisville, KY",
    "Louisiana": "New Orleans, LA",
    "Maine": "Portland, ME",
    "Maryland": "Baltimore, MD",
    "Massachusetts": "Boston, MA",
    "Michigan": "Detroit, MI",
    "Minnesota": "Minneapolis, MN",
    "Mississippi": "Jackson, MS",
    "Missouri": "Kansas City, MO",
    "Montana": "Billings, MT",
    "Nebraska": "Omaha, NE",
    "Nevada": "Las Vegas, NV",
    "New Hampshire": "Manchester, NH",
    "New Jersey": "Newark, NJ",
    "New Mexico": "Albuquerque, NM",
    "New York": "New York, NY",
    "North Carolina": "Charlotte, NC",
    "North Dakota": "Bismarck, ND",
    "Ohio": "Columbus, OH",
    "Oklahoma": "Oklahoma City, OK",
    "Oregon": "Portland, OR",
    "Pennsylvania": "Philadelphia, PA",
    "Rhode Island": "Providence, RI",
    "South Carolina": "Charleston, SC",
    "South Dakota": "Sioux Falls, SD",
    "Tennessee": "Memphis, TN",
    "Texas": "Houston, TX",
    "Utah": "Salt Lake City, UT",
    "Vermont": "Burlington, VT",
    "Virginia": "Virginia Beach, VA",
    "Washington": "Seattle, WA",
    "West Virginia": "Charleston, WV",
    "Wisconsin": "Milwaukee, WI",
    "Wyoming": "Cheyenne, WY"
}

def get_muse_jobs(category="Software Engineering", location="New York, NY", page_limit=3):
    """Fetch jobs from a single location."""
    all_jobs = []

    for page in range(page_limit):
        print(f"Fetching page {page}...")

        params = {
                "page": page,
                "category": category,
                "location": location,
                }
        response = requests.get(MUSE_URL, params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break
        data = response.json()
        results = data.get("results",[])

        if not results:
            print("No more results found.")
            break

        all_jobs.extend(results)

        time.sleep(1)
    return all_jobs


def collect_all_states(category="Software Engineering", page_limit=3):
    """Fetch Software Engineering jobs from the most populous city in each US state."""
    all_jobs = []
    state_count = 0

    print(f"\n🌍 Collecting jobs from all {len(TOP_CITIES_BY_STATE)} US states...")
    print("=" * 60)

    for state_name, city in TOP_CITIES_BY_STATE.items():
        state_count += 1
        print(f"\n[{state_count}/{len(TOP_CITIES_BY_STATE)}] Fetching from {city}...")

        try:
            jobs = get_muse_jobs(category=category, location=city, page_limit=page_limit)
            all_jobs.extend(jobs)
            print(f"  ✓ Found {len(jobs)} jobs from {city}")
        except Exception as e:
            print(f"  ✗ Error fetching from {city}: {e}")

        # Rate limiting between states
        time.sleep(2)

    print("\n" + "=" * 60)
    print(f"✓ Collection complete: {len(all_jobs)} total jobs collected from all states")
    return all_jobs

def save_to_file(data, filename="muse_jobs.json"):
    filepath = ROOT_DIR / "data" / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)
        print(f"Successfully saved {len(data)} jobs to {filepath}")

def get_google_jobs(query="software developer", location="Austin, Texas, United States"):
    """Fetch jobs from SerpAPI Google Jobs engine. Returns raw list of job dicts."""
    load_dotenv()
    api_key = os.getenv("SERP_KEY")
    if not api_key:
        raise ValueError("SERP_KEY not found in environment. Set it in .env")

    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "google_domain": "google.com",
        "hl": "en",
        "gl": "us",
        "api_key": api_key,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    jobs = results.get("jobs_results", [])
    print(f"Fetched {len(jobs)} jobs from Google Jobs for '{query}' in {location}")
    return jobs


def _parse_relative_date(posted_at):
    """Convert relative date string like '3 days ago' to ISO timestamp."""
    if not posted_at:
        return None

    now = datetime.now()
    posted_at = posted_at.lower().strip()

    match = re.match(r"(\d+)\s+(hour|day|week|month)s?\s+ago", posted_at)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "hour":
            return (now - timedelta(hours=amount)).isoformat()
        elif unit == "day":
            return (now - timedelta(days=amount)).isoformat()
        elif unit == "week":
            return (now - timedelta(weeks=amount)).isoformat()
        elif unit == "month":
            return (now - timedelta(days=amount * 30)).isoformat()

    return None


def _parse_google_salary(salary_str):
    """Parse salary from SerpAPI detected_extensions.salary.

    Handles formats like:
      '$80K - $120K a year'
      '$30 - $45 an hour'
      '$95,000 - $130,000 a year'
    Returns (salary_min, salary_max) as floats or (None, None).
    """
    if not salary_str:
        return None, None

    salary_str = salary_str.lower().strip()
    is_hourly = "hour" in salary_str

    # Find all dollar amounts
    amounts = re.findall(r"\$[\d,\.]+k?", salary_str)
    if not amounts:
        return None, None

    parsed = []
    for amt in amounts:
        num_str = amt.replace("$", "").replace(",", "")
        if num_str.endswith("k"):
            parsed.append(float(num_str[:-1]) * 1000)
        else:
            parsed.append(float(num_str))

    # Convert hourly to yearly (2080 work hours/year)
    if is_hourly:
        parsed = [p * 2080 for p in parsed]

    salary_min = parsed[0] if len(parsed) >= 1 else None
    salary_max = parsed[1] if len(parsed) >= 2 else salary_min
    return salary_min, salary_max


def _parse_google_location(location_str):
    """Parse location string like 'Austin, TX' into (city, state)."""
    if not location_str:
        return "Unknown", None

    parts = [p.strip() for p in location_str.split(",")]
    city = parts[0] if parts else "Unknown"
    state = parts[1] if len(parts) > 1 else None
    return city, state


def save_google_jobs_to_db(jobs, db_url=None):
    """Full pipeline: clean descriptions, extract skills, store in PostgreSQL.

    For each job: get-or-create company/location, parse salary/date,
    clean text, extract skills, insert into normalized DB tables.
    """
    if db_url is None:
        db_url = DATABASE_URL

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Initialize schema
    schema_path = ROOT_DIR / "data" / "schema.sql"
    with open(schema_path, "r") as f:
        cursor.execute(f.read())
    conn.commit()

    # Load skill taxonomy
    taxonomy = load_skills()

    # Caches
    company_cache = {}
    location_cache = {}
    skill_category_cache = {}
    skill_cache = {}

    run_timestamp = datetime.now().isoformat()

    stats = {
        "jobs_imported": 0,
        "jobs_updated": 0,
        "companies_created": 0,
        "locations_created": 0,
        "skill_links_created": 0,
        "errors": 0,
    }

    def get_or_create_company(name):
        if not name:
            return None
        if name in company_cache:
            return company_cache[name]
        cursor.execute("SELECT id FROM companies WHERE name = %s", (name,))
        row = cursor.fetchone()
        if row:
            company_cache[name] = row[0]
            return row[0]
        cursor.execute("INSERT INTO companies (name) VALUES (%s) RETURNING id", (name,))
        cid = cursor.fetchone()[0]
        company_cache[name] = cid
        stats["companies_created"] += 1
        return cid

    def get_or_create_location(city, state):
        key = (city, state, "USA")
        if key in location_cache:
            return location_cache[key]
        cursor.execute(
            "SELECT id FROM locations WHERE city = %s AND state = %s AND country = %s",
            key,
        )
        row = cursor.fetchone()
        if row:
            location_cache[key] = row[0]
            return row[0]
        cursor.execute(
            "INSERT INTO locations (city, state, country) VALUES (%s, %s, %s) RETURNING id", key
        )
        lid = cursor.fetchone()[0]
        location_cache[key] = lid
        stats["locations_created"] += 1
        return lid

    def get_or_create_skill_category(cat_name):
        if cat_name in skill_category_cache:
            return skill_category_cache[cat_name]
        cursor.execute("SELECT id FROM skill_categories WHERE name = %s", (cat_name,))
        row = cursor.fetchone()
        if row:
            skill_category_cache[cat_name] = row[0]
            return row[0]
        cursor.execute("INSERT INTO skill_categories (name) VALUES (%s) RETURNING id", (cat_name,))
        cid = cursor.fetchone()[0]
        skill_category_cache[cat_name] = cid
        return cid

    def get_or_create_skill(skill_name, category_name):
        key = (skill_name, category_name)
        if key in skill_cache:
            return skill_cache[key]
        cat_id = get_or_create_skill_category(category_name)
        cursor.execute(
            "SELECT id FROM skills WHERE name = %s AND category_id = %s",
            (skill_name, cat_id),
        )
        row = cursor.fetchone()
        if row:
            skill_cache[key] = row[0]
            return row[0]
        cursor.execute(
            "INSERT INTO skills (name, category_id) VALUES (%s, %s) RETURNING id",
            (skill_name, cat_id),
        )
        sid = cursor.fetchone()[0]
        skill_cache[key] = sid
        return sid

    for job in jobs:
        try:
            ext = job.get("detected_extensions", {})
            external_id = f"google_{job.get('job_id', '')}"
            title = job.get("title", "")
            company_name = job.get("company_name", "")
            location_str = job.get("location", "")
            description = job.get("description", "")

            # Company
            company_id = get_or_create_company(company_name)
            if not company_id:
                stats["errors"] += 1
                continue

            # Location
            city, state = _parse_google_location(location_str)

            # Salary
            salary_min, salary_max = _parse_google_salary(ext.get("salary"))

            # Remote detection
            schedule = ext.get("schedule_type", "")
            is_remote = "remote" in location_str.lower() or "remote" in (schedule or "").lower()

            # Posted date
            pub_date = _parse_relative_date(ext.get("posted_at"))

            # Clean description and extract skills
            cleaned = clean_job_text(description)
            skills_found = extract_skills_from_text(cleaned, taxonomy)

            # Upsert job
            cursor.execute("SELECT id FROM jobs WHERE external_job_id = %s", (external_id,))
            existing = cursor.fetchone()

            if existing:
                job_id = existing[0]
                cursor.execute(
                    """UPDATE jobs SET
                        title = %s, company_id = %s, description = %s,
                        salary_min = %s, salary_max = %s, is_remote = %s,
                        publication_date = %s, fetched_at = %s, updated_at = %s,
                        status = 'open', last_seen_at = %s
                    WHERE id = %s""",
                    (title, company_id, cleaned, salary_min, salary_max,
                     is_remote, pub_date, run_timestamp, run_timestamp,
                     run_timestamp, job_id),
                )
                stats["jobs_updated"] += 1
            else:
                cursor.execute(
                    """INSERT INTO jobs (
                        external_job_id, title, company_id, description,
                        salary_min, salary_max, is_remote, publication_date,
                        fetched_at, last_seen_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
                    RETURNING id""",
                    (external_id, title, company_id, cleaned, salary_min,
                     salary_max, is_remote, pub_date, run_timestamp,
                     run_timestamp),
                )
                job_id = cursor.fetchone()[0]
                stats["jobs_imported"] += 1

            # Link location
            location_id = get_or_create_location(city, state)
            cursor.execute(
                """INSERT INTO job_locations (job_id, location_id) VALUES (%s, %s)
                   ON CONFLICT DO NOTHING""",
                (job_id, location_id),
            )

            # Link skills
            for category, skill_list in skills_found.items():
                for skill_name in skill_list:
                    skill_id = get_or_create_skill(skill_name, category)
                    cursor.execute(
                        """INSERT INTO job_skills (job_id, skill_id) VALUES (%s, %s)
                           ON CONFLICT DO NOTHING""",
                        (job_id, skill_id),
                    )
                    stats["skill_links_created"] += 1

        except Exception as e:
            print(f"Error processing job '{job.get('title', '?')}': {e}")
            stats["errors"] += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print("Google Jobs Import Complete!")
    print("=" * 50)
    print(f"Jobs imported:      {stats['jobs_imported']}")
    print(f"Jobs updated:       {stats['jobs_updated']}")
    print(f"Companies created:  {stats['companies_created']}")
    print(f"Locations created:  {stats['locations_created']}")
    print(f"Skill links:        {stats['skill_links_created']}")
    print(f"Errors:             {stats['errors']}")
    print("=" * 50 + "\n")

    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "google":
        query = sys.argv[2] if len(sys.argv) > 2 else "software developer"
        location = sys.argv[3] if len(sys.argv) > 3 else "Austin, Texas, United States"
        jobs = get_google_jobs(query=query, location=location)
        save_google_jobs_to_db(jobs)
    else:
        # Default: Muse collection
        jobs = get_muse_jobs(category="Software Engineering", location="New York, NY", page_limit=25)
        save_to_file(jobs)
