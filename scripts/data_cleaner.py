import nltk
import json
import pandas as pd
from bs4 import BeautifulSoup
import re
import unicodedata
from nltk.tokenize import RegexpTokenizer
from nltk.util import ngrams

def clean_job_text(text):
    soup = BeautifulSoup(text,"lxml")
    for element in soup(['script','style','header','footer']):
        element.decompose()

    text = soup.get_text(separator=" ")

    text = unicodedata.normalize("NFKD",text)
    
    # Removes URL's and emails
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)

    text = re.sub(r'[^a-zA-Z0-9 \+\#\.\,\-\$\:]', ' ', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_text_column(df):
    df['clean_description'] = df['contents'].apply(clean_job_text)
    return df

def pull_salary_data(text):
    pattern = r'(\$[0-9][0-9,\.]*[kK]?\s*(?:-|to)?\s*\$?[0-9][0-9,\.]*[kK]?)'
    match = re.search(pattern,text)
    if match:
        return match.group(0)
    return None

def pull_column_salary(df):
    df['salary'] = df['clean_description'].apply(pull_salary_data)
    return df

def load_skills(filename="skills.json"):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            for category in data:
                data[category] = set(data[category])
            return data
    except FileNotFoundError:
        print(f"Error: Could not find {filename}")
        return {}

def extract_skills(text,taxonomy):
    text = text.lower()

    tokenizer = RegexpTokenizer(r'[a-zA-Z0-9]+(?:\+\+|#|\.[a-z]+)?')
    tokens = tokenizer.tokenize(text)

    bigrams = [" ".join(bg) for bg in ngrams(tokens,2)]
    all_tokens = tokens + bigrams
    found_skills = {category: [] for category in taxonomy}
    for token in all_tokens:
        for category, keywords in taxonomy.items():
            if token in keywords:
                found_skills[category].append(token)

    for cat in found_skills:
        found_skills[cat] = list(set(found_skills[cat]))
        
    return found_skills

with open('muse_jobs.json', 'r') as f:
    data = json.load(f)

df = pd.json_normalize(data)
df = clean_text_column(df)
print(df.at[1,'clean_description'])
taxonomy = load_skills()
found_skills = extract_skills(df.at[1,'clean_description'],taxonomy)
print(found_skills)
df = pull_column_salary(df)
#for i in range(100):
#    print(df.at[i,'salary'])
