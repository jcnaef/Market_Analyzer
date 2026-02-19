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
* `ai_data_cleaner.py`: Parses the JSON, strips HTML, extracts salaries/locations, and matches text against a skill taxonomy. Outputs a clean `processed_jobs.csv`.
* `nlp.py`: An experimental advanced extraction module utilizing `spaCy` (`en_core_web_lg`) and `SkillExtractor` for deep semantic parsing.
* `debug.py`: A diagnostic utility to verify data integrity.

### Database & Backend (FastAPI)
* `market_analyzer.db`: SQLite database containing jobs, skills, locations, and their relationships (created by migration scripts).
* `migrate_to_sqlite.py`: Migration script that populates the SQLite database from processed CSV data.
* `verify_database.py`: Utility to verify database integrity and schema.
* `ai_skill_recommendation.py`: Queries the database to calculate skill co-occurrence probabilities and identify related skills.
* `ai_location_skill_recommendation.py`: Queries the database to identify the most in-demand skills by location or remote status.
* `recommendation_api.py`: The FastAPI application that exposes the recommendation engines via REST endpoints (`/skill/{name}` and `/location/{city}`).

### Frontend (React)
* `App.jsx`: The main React component that handles state, API fetching, and rendering the interactive results dashboard.

## Prerequisites
* **Backend:** Python 3.8+, `pandas`, `nltk`, `beautifulsoup4`, `fastapi`, `uvicorn`, `requests`, `spacy`, `skillNer`
* **Frontend:** Node.js and `npm` (or `yarn`)
* A valid `skills.json` taxonomy file in the root directory.

## Installation & Setup

### 1. Build the Data Model
First, fetch the raw data and run it through the cleaning pipeline to generate the CSV.
```bash
python src/market_analyzer/api_handler.py
python src/market_analyzer/ai_data_cleaner.py
```

### 2. Populate the Database
Migrate the processed CSV data into the SQLite database.
```bash
python migrate_to_sqlite.py
python verify_database.py
```

### 3. Start the Backend API
Launch the FastAPI server. It will run on port 8000 and handle requests from the frontend.
```bash
./run.sh
```

### 4. Start the React Frontend
Open a new terminal window, navigate to your frontend directory, install the dependencies, and start the development server (typically runs on port 5173).
```bash
./start_frontend.sh
```
### API Endpoints
If interacting directly with the backend (http://127.0.0.1:8000):
* GET /skill/{skill_name}: Returns the top 10 skills most frequently associated with a target skill
* GET /location/{city}: Returns the top in-demand skills for a specific city or for Remote roles

