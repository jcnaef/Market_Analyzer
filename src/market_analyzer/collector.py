import requests
import json
import time
from pathlib import Path

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

if __name__ == "__main__":
    # Single-location usage for backward compatibility
    jobs = get_muse_jobs(category="Software Engineering", location="New York, NY", page_limit=25)
    save_to_file(jobs)
