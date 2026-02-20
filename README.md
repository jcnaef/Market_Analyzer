# Job Market Skill Recommender

A full-stack application that analyzes software engineering job postings from The Muse API and provides actionable career insights. Discover in-demand skills, explore salary trends, identify skill gaps, and analyze your resume against current market demands.

## Features

- **Dashboard** — Overview of top skills, job statistics, and remote vs. onsite distribution
- **Job Board** — Filterable, paginated job listings with search, level, location, and skill filters
- **Skill Explorer** — Search skill correlations and view location-based skill demand trends
- **Salary Insights** — Box plot visualizations of salary distributions by job level or skill
- **Skill Gap Analyzer** — Input your known skills and get recommendations for high-demand skills to learn
- **Resume Analyzer** — Upload a PDF/DOCX resume to extract skills and compare against market demand

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.10+, FastAPI, SQLite, pandas, NLTK, BeautifulSoup4 |
| **Frontend** | React 19, Vite, Tailwind CSS, Recharts, React Router |
| **Testing** | pytest (86 tests) |
| **Package Management** | Poetry (Python), npm (Node) |

## Project Structure

```
Market_Analyzer/
├── src/market_analyzer/       # Backend modules
│   ├── server.py              # FastAPI REST API
│   ├── collector.py           # Fetches jobs from The Muse API
│   ├── cleaner.py             # HTML cleaning and skill extraction
│   ├── skill_recommender.py   # Skill co-occurrence analysis
│   ├── location_recommender.py# Location-based skill demand
│   ├── db_queries.py          # Database query utilities
│   └── nlp_models.py          # Advanced NLP extraction (spaCy)
├── frontend/src/              # React frontend
│   ├── pages/                 # Dashboard, JobBoard, SkillExplorer,
│   │                          # SalaryInsights, SkillGapAnalyzer, ResumeAnalyzer
│   ├── components/            # Reusable UI components
│   ├── App.jsx                # Routing
│   └── api.js                 # API client
├── scripts/                   # Data pipeline scripts
├── data/                      # SQLite database and schema
├── tests/                     # Test suite
├── pyproject.toml             # Python dependencies
└── run.sh                     # Backend startup script
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js
- [Poetry](https://python-poetry.org/)

### 1. Install Dependencies

```bash
# Backend
poetry install

# Frontend
cd frontend && npm install
```

### 2. Build the Data Model

Fetch raw job data and run the cleaning pipeline:

```bash
python src/market_analyzer/collector.py
python src/market_analyzer/cleaner.py
```

### 3. Populate the Database

Migrate processed data into SQLite:

```bash
python scripts/migrate_to_sqlite.py
```

### 4. Start the Application

```bash
# Terminal 1 — Backend API (http://localhost:8000)
./run.sh

# Terminal 2 — Frontend dev server (http://localhost:5173)
cd frontend && npm run dev
```

### Running Tests

```bash
pytest tests/
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/skill/{name}` | Top 10 correlated skills |
| `GET` | `/location/{city}` | In-demand skills for a location |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `GET` | `/api/jobs` | Paginated job listings (supports filters) |
| `GET` | `/api/salary/insights` | Salary analysis by level or skills |
| `POST` | `/api/skill-gap/analyze` | Skill gap analysis |
| `POST` | `/api/resume/analyze` | Resume upload and analysis |
| `GET` | `/skills/autocomplete` | Skill search suggestions |
| `GET` | `/locations/autocomplete` | Location search suggestions |
