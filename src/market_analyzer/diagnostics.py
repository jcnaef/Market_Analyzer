import pandas as pd
from pathlib import Path
from .location_recommender import LocationSkillRecommender

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 1. Check the raw CSV data
print("--- CSV DIAGNOSTIC ---")
df = pd.read_csv(ROOT_DIR / "data" / "processed_jobs.csv")

if 'job_city' not in df.columns:
    print("❌ ERROR: 'job_cities' column is MISSING from your CSV.")
    print("   Please run 'python data_cleaner.py' again.")
else:
    # Show us what the first few rows look like
    print(f"First 5 rows of 'job_cities':")
    print(df['job_city'].head(5))
    
    # Check if they are all empty
    non_empty = df[df['job_city'] != "[]"]
    print(f"Rows with cities found: {len(non_empty)} out of {len(df)}")

# 2. Check the Brain
print("\n--- BRAIN DIAGNOSTIC ---")
try:
    brain = LocationSkillRecommender(str(ROOT_DIR / "data" / "processed_jobs.csv"))
    print(f"Total Locations in Matrix: {len(brain.location_matrix.index)}")
    print("Available Locations:")
    print(sorted(brain.location_matrix.index.tolist()))
except Exception as e:
    print(f"❌ Brain failed to load: {e}")
