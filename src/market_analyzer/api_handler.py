import requests
import json
import time
from pathlib import Path
# TODO Implement JSEARCH for more data

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

#from dotenv import load_dotenv

#load_dotenv()
#api_key = os.getenv("JSEARCH_KEY")

#JSEARCH_URL = "https://jsearch.p.rapidapi.com/job-details"

#def get_jsearch_jobs(

MUSE_URL = "https://www.themuse.com/api/public/jobs"
def get_muse_jobs(category="Software Engineering", location = "New York, NY", page_limit=3):
    all_jobs = []

    for page in range(page_limit):
        print(f"Fetching page {page}...")

        params = {
                "page": page,
                "category": category,
                "location": location,
                "api_key": API_KEY
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

def save_to_file(data, filename="muse_jobs.json"):
    filepath = ROOT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)
        print(f"Successfully saved {len(data)} jobs to {filepath}")

if __name__ == "__main__":
    jobs = get_muse_jobs(category="Software Engineering", location = "New York, NY",page_limit=25)
    save_to_file(jobs)
