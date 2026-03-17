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
#jobs_results = results["jobs"]
print(results)
#print(jobs_results)
