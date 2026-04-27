# Job Market Skill Recommender
![Project Screenshot] (./images/career_logic.png)

**Live site:** [careerlogic.info](https://www.careerlogic.info)

A full-stack AI-powered job market analysis platform that helps software engineers discover in-demand skills, explore salary trends, identify skill gaps, and tailor resumes to job descriptions. It aggregates job postings from **The Muse API** and **Google Jobs (via SerpAPI)** and provides actionable career insights.

## Features

- **Dashboard** — Overview of top skills, job statistics, monthly posting trends, and remote vs. onsite distribution
- **Job Board** — Filterable, paginated job listings with search, level, location, skill, and remote filters
- **Skill Explorer** — Search skill correlations and view location-based skill demand trends
- **Salary Insights** — Box plot visualizations of salary distributions by job level or skill
- **Skill Gap Analyzer** — Input your known skills and get recommendations for high-demand skills to learn
- **Resume Analyzer** — Upload a PDF/DOCX resume to extract skills and compare against market demand
- **Resume Tailoring** — LLM-powered bullet point adaptation with side-by-side diff review, skill suggestions, and PDF export (requires login)
- **User Accounts** — Google OAuth via Firebase, persistent resume storage, and tailoring history

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.10+, FastAPI, PostgreSQL, pandas, NLTK, BeautifulSoup4 |
| **Data Sources** | The Muse API, Google Jobs via SerpAPI |
| **Frontend** | React 19, Vite, Tailwind CSS, Recharts, React Router |
| **Auth** | Firebase Auth (Google OAuth), Firebase Admin SDK |
| **AI/LLM** | Groq API (Llama 3) |
| **Testing** | pytest |
| **Deployment** | Docker |
| **Package Management** | Poetry (Python), npm (Node) |

## Project Structure

```
Market_Analyzer/
├── src/market_analyzer/        # Backend modules
│   ├── server.py               # FastAPI REST API (all endpoints)
│   ├── db_config.py            # Database connection pooling & Firebase init
│   ├── db_queries.py           # Database query utilities
│   ├── auth.py                 # Firebase authentication dependency
│   ├── collector.py            # Fetches jobs from The Muse API and Google Jobs (SerpAPI)
│   ├── cleaner.py              # HTML cleaning and skill extraction
│   ├── resume_parser.py        # Rule-based resume parsing (PDF/DOCX → structured JSON)
│   ├── text_extractor.py       # PDF and DOCX text extraction
│   ├── tailoring.py            # LLM-powered resume bullet tailoring
│   ├── skill_recommender.py    # Skill co-occurrence analysis
│   ├── skill_suggester.py      # Job description skill suggestions
│   ├── location_recommender.py # Location-based skill demand
│   ├── rate_limiter.py         # Per-user and global rate limiting
│   ├── schemas.py              # Pydantic request/response models
│   └── backfill_salary.py      # Salary data backfilling utility
├── frontend/src/               # React frontend
│   ├── pages/                  # Dashboard, JobBoard, SkillExplorer,
│   │                           # SalaryInsights, ResumeAnalyzer,
│   │                           # AccountPage, TailoringPage
│   ├── components/             # Reusable UI components
│   ├── context/                # Auth and Resume contexts
│   ├── config/                 # Firebase configuration
│   ├── App.jsx                 # Routing
│   └── api.js                  # API client
├── migrations/                 # PostgreSQL migrations (applied automatically on startup)
├── scripts/                    # Data pipeline scripts
│   ├── cron_collect.py         # Orchestrates SerpAPI + Muse collection within API budgets
│   ├── close_jobs.py           # Marks stale postings inactive
│   ├── run_migrations.py       # Manual migration runner
│   └── visualize_db.py         # DB inspection utility
├── tests/                      # Test suite
├── Dockerfile                  # Container deployment
├── pyproject.toml              # Python dependencies
├── requirements.txt            # Pip dependencies (for Docker)
└── run.sh                      # Development startup script
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js
- PostgreSQL
- [Poetry](https://python-poetry.org/)

### 1. Install Dependencies

```bash
# Backend
poetry install

# Frontend
cd frontend && npm install
```

### 2. Configure Environment

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@localhost:5432/market_analyzer
GROQ_API_KEY=your_groq_api_key
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_CLIENT_EMAIL=your_service_account_email
FIREBASE_PRIVATE_KEY=your_private_key
SERP_KEY=your_serpapi_key          # SerpAPI key for Google Jobs collection
ALLOWED_ORIGINS=*                  # CORS origins
```

### 3. Build the Data Model

Fetch raw job data and run the cleaning pipeline. Skill extraction and persistence happen inside `collector.py`:

```bash
# One-off collection from each source
python src/market_analyzer/collector.py            # Muse (default)
python src/market_analyzer/collector.py google     # Google Jobs (SerpAPI)

# Or use the cron orchestrator (respects per-source API budgets and rotates queries/states)
python scripts/cron_collect.py serp                # SerpAPI daily rotation
python scripts/cron_collect.py muse                # Muse weekly rotation
python scripts/cron_collect.py all                 # Both sources in sequence
python scripts/cron_collect.py status              # Show usage and rotation state
```

SerpAPI is capped at ~1,000 searches/month — `cron_collect.py` rotates 25 states per day and stays well under the 200/hr ceiling. Muse has no monthly cap but is throttled at 250 searches/hour.

### 4. Start the Application

Database migrations run automatically on startup.

```bash
# Terminal 1 — Backend API (http://localhost:8000)
./run.sh

# Terminal 2 — Frontend dev server (http://localhost:5173)
cd frontend && npm run dev
```

### Docker

```bash
docker build -t market-analyzer .
docker run -p 8000:8000 --env-file .env market-analyzer
```

### Running Tests

Tests run against a real `market_analyzer_test` PostgreSQL database (no DB mocks). The schema is built from `data/schema.sql` and torn down between tests.

```bash
poetry run pytest                          # All tests
poetry run pytest tests/test_server.py     # Single file
poetry run pytest -k "test_name"           # Single test by name
```

## API Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/skill/{name}` | Top correlated skills |
| `GET` | `/location/{city}` | In-demand skills for a location |
| `GET` | `/skills/autocomplete` | Skill search suggestions |
| `GET` | `/locations/autocomplete` | Location search suggestions |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `GET` | `/api/jobs` | Paginated job listings (supports filters) |
| `GET` | `/api/jobs/{job_id}` | Single job details |
| `GET` | `/api/salary/insights` | Salary analysis by level or skill |
| `POST` | `/api/skill-gap/analyze` | Skill gap analysis |
| `POST` | `/api/resume/analyze` | Resume upload and analysis |
| `POST` | `/api/suggest-skills` | Suggest missing skills from job description |
| `GET` | `/api/filters/levels` | Available job levels |
| `GET` | `/api/filters/locations` | Available locations |

### Authenticated (Firebase)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/user/me` | Current user info |
| `POST` | `/api/user/resume/upload` | Upload and parse resume (PDF/DOCX, max 5MB) |
| `GET` | `/api/user/resume` | Retrieve saved resume |
| `PUT` | `/api/user/resume` | Save resume data |
| `POST` | `/api/tailor-section` | Tailor resume bullets via LLM (rate-limited) |
