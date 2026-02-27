from serpapi import GoogleSearch
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
my_key = os.getenv("SERP_KEY")
params = {
  "engine": "google_jobs",
  "location": "Austin, Texas, United States",
  "google_domain": "google.com",
  "hl": "en",
  "gl": "us",
  "q": "software developer",
  "api_key": my_key
}

search = GoogleSearch(params)
results = search.get_dict()
jobs_results = results["jobs_results"]

rows = []
for job in jobs_results:
    row = {
        "title": job.get("title"),
        "company_name": job.get("company_name"),
        "location": job.get("location"),
        "description": job.get("description"),
        "extensions": ", ".join(str(v) for v in job.get("detected_extensions", {}).values()),
        "schedule_type": job.get("detected_extensions", {}).get("schedule_type"),
        "salary": job.get("detected_extensions", {}).get("salary"),
        "posted_at": job.get("detected_extensions", {}).get("posted_at"),
        "via": job.get("via"),
    }
    rows.append(row)

df = pd.DataFrame(rows)
output_path = os.path.join(os.path.dirname(__file__), "..", "data", "google_jobs.csv")
df.to_csv(output_path, index=False)
print(f"Exported {len(df)} jobs to {output_path}")
print(df.head())
