# Job Market Skill Recommender (Full-Stack)

## Overview
The Job Market Skill Recommender is a full-stack data engineering and machine learning application designed to analyze software engineering job postings and provide actionable career insights. 

It features an automated data pipeline that fetches real job descriptions, an NLP engine to extract and normalize technical skills, a FastAPI backend to calculate skill co-occurrences, and a React frontend for users to interactively explore what skills are most in-demand by location or tech stack.

## Key Features
* **Full-Stack UI:** A responsive React dashboard (`App.jsx`) that visualizes skill correlations and location-based job market trends.
* **Automated Data Ingestion:** Fetches software engineering job postings directly from The Muse API.
* **Advanced NLP Processing:** Cleans HTML artifacts using `BeautifulSoup` and extracts entities. The project supports both taxonomy-based regex extraction and advanced Named Entity Recognition (NER) using `spaCy` and `skillNer`.
* **Recommendation Engines:** Calculates the probability of skill pairings using a normalized co-occurrence matrix, and maps out geographic/remote skill trends.
* **Diagnostic Tooling:** Built-in debugging scripts to verify matrix integrity and data parsing.

## Project Structure

### Data Pipeline & NLP
* `api_handler.py`: Pings The Muse API and downloads raw job listings into `muse_jobs.json`.
* `ai_data_cleaner.py` / `data_cleaner.py`: Parses the JSON, strips HTML, extracts salaries/locations, and matches text against a skill taxonomy. Outputs a clean `processed_jobs.csv`.
* `nlp.py`: An experimental advanced extraction module utilizing `spaCy` (`en_core_web_lg`) and `SkillExtractor` for deep semantic parsing.
* `debug.py`: A diagnostic utility to verify the integrity of the generated CSV and ensure the recommendation matrices load correctly.

### Backend (FastAPI)
* `ai_skill_recommendation.py`: Builds a statistical matrix from the processed CSV to calculate cross-skill probabilities.
* `ai_location_skill_recommendation.py`: Builds a matrix mapping geographic locations (and "Remote" status) to the most requested technical skills.
* `recommendation_api.py`: The FastAPI application that exposes the recommendation engines via REST endpoints (`/skill/{name}` and `/location/{city}`).

### Frontend (React)
* `App.jsx`: The main React component that handles state, API fetching, and rendering the interactive results dashboard.

## Prerequisites
* **Backend:** Python 3.8+, `pandas`, `nltk`, `beautifulsoup4`, `fastapi`, `uvicorn`, `requests`, `spacy`, `skillNer`
* **Frontend:** Node.js and `npm` (or `yarn`)
* A valid `skills.json` taxonomy file in the root directory.

## Installation & Setup

### 1. Build the Data Model
First, fetch the raw data and run it through the cleaning pipeline to generate your recommendation matrices.
```bash
python api_handler.py
python ai_data_cleaner.py
```

### 2. Start the Backend API
Launch the FASTAPI server. It will run on port 8000 and handle requests from the frontend
```bash
./run.sh
```

### 3. Start the React Frontend
Open a new terminal window, navigate to your frontend directory, install the dependencies, and start the development server (typically runs on port 5173).
```bash
./start_frontend.sh
```
### API Endpoints
If interacting directly with the backend (http://127.0.0.1:8000):
* GET /skill/{skill_name}: Returns the top 10 skills most frequently associated with a target skill
* GET /location/{city}: Returns the top in-demand skills for a specific city or for Remote roles

