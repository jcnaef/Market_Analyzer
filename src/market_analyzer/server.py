import sqlite3
import tempfile
import os
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from .skill_recommender import SkillRecommender
from .location_recommender import LocationSkillRecommender
from . import db_queries
from .cleaner import extract_skills_from_text, load_skills

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
db_file = ROOT_DIR / "data" / "market_analyzer.db"
if db_file.exists():
    skill_brain = SkillRecommender(str(db_file))
    location_brain = LocationSkillRecommender(str(db_file))
else:
    skill_brain = None
    location_brain = None

DB_PATH = str(db_file)

# Load skill taxonomy once for resume analysis
_taxonomy = load_skills()


# --- Pydantic models ---

class SkillGapRequest(BaseModel):
    known_skills: list[str]


# --- Original endpoints ---

@app.get("/")
def home():
    return {"message": "Go to /skill/{skill_name} to see correlations"}


@app.get("/skill/{name}")
def get_skill_matrix(name: str):
    if not skill_brain:
        raise HTTPException(status_code=500, detail="Server Error: Data file not found")
    results = skill_brain.get_skill_recommendations(name)
    if results is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found in database")
    return {"target_skill": name, "related_skills": results}


@app.get("/location/{city}")
def get_city_stats(city: str):
    if not location_brain:
        raise HTTPException(status_code=500, detail="location model not loaded")
    results = location_brain.get_location_trends(city)
    if not results:
        raise HTTPException(status_code=404, detail="Location not found")
    return results


@app.get("/skills/autocomplete")
def skills_autocomplete(q: str = "", limit: int = 8):
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    if not skill_brain:
        raise HTTPException(status_code=500, detail="Skill database not available")
    prefix = q.lower() + "%"
    try:
        conn = sqlite3.connect(skill_brain.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT s.name FROM skills s
               JOIN skill_categories sc ON s.category_id = sc.id
               WHERE LOWER(s.name) LIKE LOWER(?) AND sc.name != 'Soft_Skills'
               ORDER BY s.name ASC LIMIT ?""",
            (prefix, limit),
        )
        results = cursor.fetchall()
        conn.close()
        return {"suggestions": [row[0] for row in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/locations/autocomplete")
def locations_autocomplete(q: str = "", limit: int = 8):
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    if not location_brain:
        raise HTTPException(status_code=500, detail="Location database not available")
    try:
        matches = [loc for loc in location_brain.known_locations if loc.lower().startswith(q.lower())]
        return {"suggestions": sorted(matches)[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering locations: {str(e)}")


# --- New API endpoints ---

@app.get("/api/dashboard/stats")
def dashboard_stats():
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    return db_queries.get_dashboard_stats(DB_PATH)


@app.get("/api/jobs")
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    level: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    remote_only: bool = False,
    search: str | None = None,
    sort: str = "date_desc",
):
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    return db_queries.get_jobs(
        DB_PATH, page=page, per_page=per_page, level=level,
        location=location, skill=skill, remote_only=remote_only,
        search=search, sort=sort,
    )


@app.get("/api/salary/insights")
def salary_insights(group_by: str = "level", names: str | None = None):
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    name_list = [n.strip() for n in names.split(",") if n.strip()] if names else None
    result = db_queries.get_salary_insights(DB_PATH, group_by=group_by, names=name_list)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/skill-gap/analyze")
def skill_gap_analyze(request: SkillGapRequest):
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    return db_queries.analyze_skill_gap(DB_PATH, request.known_skills)


@app.post("/api/resume/analyze")
async def resume_analyze(file: UploadFile = File(...)):
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    contents = await file.read()

    # Write to temp file for parsing
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        if ext == "pdf":
            import pdfplumber
            text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:  # docx
            from docx import Document
            doc = Document(tmp_path)
            text = "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    # Extract skills using existing taxonomy
    extracted = extract_skills_from_text(text, _taxonomy)

    return db_queries.analyze_resume_skills(DB_PATH, extracted)


@app.get("/api/filters/levels")
def filter_levels():
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    return {"levels": db_queries.get_filter_levels(DB_PATH)}


@app.get("/api/filters/locations")
def filter_locations():
    if not db_file.exists():
        raise HTTPException(status_code=500, detail="Database not available")
    return {"locations": db_queries.get_filter_locations(DB_PATH)}
