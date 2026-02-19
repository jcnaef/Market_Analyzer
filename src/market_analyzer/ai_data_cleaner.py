import nltk
import json
import ast
import pandas as pd
import re
import unicodedata
import os
from pathlib import Path
from bs4 import BeautifulSoup
from nltk.tokenize import RegexpTokenizer
from nltk.util import ngrams

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Ensure NLTK data is present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def load_skills(filename="skills.json"):
    """
    Loads skill taxonomy from a JSON file and converts lists to sets for faster O(1) lookups.
    """
    filepath = ROOT_DIR / filename
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found. Skill extraction will be skipped.")
        return {}

    with open(filepath, 'r') as file:
        data = json.load(file)
        for category in data:
            data[category] = set(data[category])
        return data

def load_job_data(filename):
    """
    Loads job data from a JSON file and normalizes it into a DataFrame.
    """
    filepath = ROOT_DIR / filename
    if not os.path.exists(filepath):
        print(f"Error: Input file '{filepath}' not found.")
        return pd.DataFrame()

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Normalize nested JSON into a flat table
        df = pd.json_normalize(data)
        print(f"Successfully loaded {len(df)} job listings from {filepath}.")
        return df

    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {filepath}. Check file format.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred loading data: {e}")
        return pd.DataFrame()

def clean_job_text(text):
    """
    Parses HTML, removes noise (emails, URLs), and normalizes text.
    """
    if not isinstance(text, str):
        return ""

    # 1. HTML Parsing
    soup = BeautifulSoup(text, "lxml")
    for element in soup(['script', 'style', 'header', 'footer']):
        element.decompose()
    
    text = soup.get_text(separator=" ")

    # 2. Unicode Normalization
    text = unicodedata.normalize("NFKD", text)
    
    # 3. Regex Cleaning
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove Emails
    text = re.sub(r'\S+@\S+', '', text)

    # Whitelist Filter: Keep ONLY alphanumeric, spaces, and specific punctuation
    text = re.sub(r'[^a-zA-Z0-9 \+\#\.\,\-\$\:]', ' ', text)

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_location_info(loc_input):
    """
    Input:  "[{'name': 'Flexible / Remote'}, {'name': 'New York, NY'}, {'name': 'Seattle, WA'}]"
    Output: (['New York', 'Seattle'], True)
    """
    cities = []
    is_remote = False
    
    try:
        if not isinstance(loc_input, list):
            return [], False
            
        loc_data = loc_input
            
        names = [l.get('name', 'Unknown') for l in loc_data]
        
        for name in names:
            lower_name = name.lower()
            
            # Check for Remote
            if "remote" in lower_name or "flexible" in lower_name:
                is_remote = True
            
            # Check for Physical City
            # We treat anything NOT "remote" as a city
            elif "united states" not in lower_name: # Filter out generic "United States" tags if you want
                # Clean "New York, NY" -> "New York"
                clean_city = name.split(",")[0].strip()
                if clean_city not in cities:
                    cities.append(clean_city)
                
        return cities, is_remote

    except:
        return [], False
def extract_salary(text):
    """
    Attempts to pull salary ranges using Regex.
    """
    pattern = r'(\$[0-9][0-9,\.]*[kK]?\s*(?:-|to)?\s*\$?[0-9][0-9,\.]*[kK]?)'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None

def extract_skills_from_text(text, taxonomy):
    """
    Tokenizes text and finds matches against the skill taxonomy.
    """
    if not taxonomy:
        return {}

    text = text.lower()

    # Regex Tokenizer for tech terms
    tokenizer = RegexpTokenizer(r'[a-zA-Z0-9]+(?:\+\+|#|\.[a-z]+)?')
    tokens = tokenizer.tokenize(text)

    # Generate Bigrams
    bigrams = [" ".join(bg) for bg in ngrams(tokens, 2)]
    all_tokens = tokens + bigrams
    
    found_skills = {category: [] for category in taxonomy}
    
    for token in all_tokens:
        for category, keywords in taxonomy.items():
            if token in keywords:
                found_skills[category].append(token)

    for cat in found_skills:
        found_skills[cat] = list(set(found_skills[cat]))
        
    return found_skills

def process_dataset(data_file, skills_file="skills.json"):
    """
    Main driver function.
    """
    # 1. Load Data using our new functions
    taxonomy = load_skills(skills_file)
    df = load_job_data(data_file)
    
    if df.empty:
        return df

    # 2. Clean Text
    print("Cleaning text descriptions...")
    df['clean_description'] = df['contents'].apply(clean_job_text)

    # 3. Extract Salary
    print("Extracting salary data...")
    df['salary'] = df['clean_description'].apply(extract_salary)

    # 4. Extract Skills
    print("Extracting skills...")
    df['skills_data'] = df['clean_description'].apply(
        lambda x: extract_skills_from_text(x, taxonomy)
    )
    # 5. Extract Location
    print("Separating City and Remote status...")

    # Apply function to get tuples: ("New York", True)
    if 'locations' in df.columns:
        location_data = df['locations'].apply(extract_location_info)

        # Split the tuple into two columns
        df['job_city'] = location_data.apply(lambda x: x[0])
        df['is_remote'] = location_data.apply(lambda x: x[1])
    else:
        df['job_city'] = "Unknown"
        df['is_remote'] = False

    # 6. Expand Skills into Columns
    skills_df = pd.json_normalize(df['skills_data'])
    skills_df.columns = [f"skills_{c}" for c in skills_df.columns]
    
    df = pd.concat([df, skills_df], axis=1)

    print("Processing complete.")
    return df

# --- Entry Point ---
if __name__ == "__main__":
    input_file = 'muse_jobs.json'

    final_df = process_dataset(input_file)

    if not final_df.empty:
        print("\n--- Data Preview ---")
        # Adjust these column names based on what actually exists in your data
        cols_to_show = ['job_city', 'is_remote']
        existing_cols = [c for c in cols_to_show if c in final_df.columns]
        print(final_df[existing_cols].head())
        output_path = ROOT_DIR / "processed_jobs.csv"
        final_df.to_csv(output_path, index=False)
