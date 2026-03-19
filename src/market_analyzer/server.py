import tempfile
import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel

from .db_config import DATABASE_URL, init_pool, close_pool, get_db, init_firebase
from .skill_recommender import SkillRecommender
from .location_recommender import LocationSkillRecommender
from . import db_queries
from .cleaner import extract_skills_from_text, load_skills
from .text_extractor import extract_text_from_file
from .resume_parser import parse_resume
from .schemas import ResumeSchema
from .skill_suggester import suggest_skills
from .tailoring import tailor_bullets
from .rate_limiter import check_rate_limit
from .auth import get_current_user

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Module-level state (set during lifespan startup)
skill_brain = None
location_brain = None
_taxonomy = None


@asynccontextmanager
async def lifespan(app):
    global skill_brain, location_brain, _taxonomy

    # Startup
    init_firebase()
    init_pool()
    try:
        skill_brain = SkillRecommender(DATABASE_URL)
        location_brain = LocationSkillRecommender(DATABASE_URL)
    except Exception:
        skill_brain = None
        location_brain = None
    _taxonomy = load_skills()

    yield

    # Shutdown
    close_pool()


app = FastAPI(lifespan=lifespan)

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic models ---

class SkillGapRequest(BaseModel):
    known_skills: list[str]


class SkillSuggestRequest(BaseModel):
    job_description: str
    user_skills: list[str]


class TailorRequest(BaseModel):
    original_bullets: list[str]
    job_description: str
    allowed_additions: list[str] = []
    experience_company: str = ""
    experience_title: str = ""


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
        with get_db(skill_brain.db_url) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT s.name FROM skills s
                   JOIN skill_categories sc ON s.category_id = sc.id
                   WHERE LOWER(s.name) LIKE LOWER(%s) AND sc.name != 'Soft_Skills'
                   ORDER BY s.name ASC LIMIT %s""",
                (prefix, limit),
            )
            results = cursor.fetchall()
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

@app.get("/api/jobs/{job_id}")
def get_job_by_id(job_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, description FROM jobs WHERE id = %s",
            (job_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": row[0], "title": row[1], "description": row[2]}


@app.get("/api/dashboard/stats")
def dashboard_stats():
    return db_queries.get_dashboard_stats()


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
    return db_queries.get_jobs(
        page=page, per_page=per_page, level=level,
        location=location, skill=skill, remote_only=remote_only,
        search=search, sort=sort,
    )


@app.get("/api/salary/insights")
def salary_insights(group_by: str = "level", names: str | None = None):
    name_list = [n.strip() for n in names.split(",") if n.strip()] if names else None
    result = db_queries.get_salary_insights(group_by=group_by, names=name_list)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/skill-gap/analyze")
def skill_gap_analyze(request: SkillGapRequest):
    return db_queries.analyze_skill_gap(known_skills=request.known_skills)


@app.post("/api/resume/analyze")
async def resume_analyze(file: UploadFile = File(...)):
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
        text = extract_text_from_file(tmp_path, ext)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    # Extract skills using existing taxonomy
    extracted = extract_skills_from_text(text, _taxonomy)

    return db_queries.analyze_resume_skills(extracted_skills=extracted)


@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


@app.post("/api/user/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        text = extract_text_from_file(tmp_path, ext)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    parsed = parse_resume(text)
    return parsed


@app.put("/api/user/resume")
def save_resume(
    resume: ResumeSchema,
    user: dict = Depends(get_current_user),
):
    import json
    resume_json = json.loads(resume.model_dump_json())

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO resumes (user_id, resume_data)
               VALUES (%s, %s::jsonb)
               ON CONFLICT (user_id) DO UPDATE
               SET resume_data = EXCLUDED.resume_data, updated_at = NOW()""",
            (user["id"], json.dumps(resume_json)),
        )
        cur.execute(
            "UPDATE users SET has_resume = TRUE, updated_at = NOW() WHERE id = %s",
            (user["id"],),
        )
        conn.commit()

    return {"status": "saved"}


@app.get("/api/user/resume")
def get_resume(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT resume_data FROM resumes WHERE user_id = %s",
            (user["id"],),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No resume found")

    return row[0]


@app.post("/api/tailor-section")
def tailor_section(
    request: TailorRequest,
    user: dict = Depends(get_current_user),
):
    import json as _json

    allowed, msg = check_rate_limit(user["id"])
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    result = tailor_bullets(
        original_bullets=request.original_bullets,
        job_description=request.job_description,
        allowed_additions=request.allowed_additions,
        taxonomy=_taxonomy,
        experience_title=request.experience_title,
        experience_company=request.experience_company,
    )

    # Save to history
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO tailoring_history
               (user_id, experience_company, experience_title,
                original_bullets, tailored_bullets, job_description,
                allowed_additions, warnings)
               VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s::jsonb)""",
            (
                user["id"],
                request.experience_company,
                request.experience_title,
                _json.dumps(result["original"]),
                _json.dumps(result["tailored"]),
                request.job_description,
                _json.dumps(request.allowed_additions),
                _json.dumps(result["warnings"]),
            ),
        )
        conn.commit()

    return result


@app.post("/api/suggest-skills")
def suggest_skills_endpoint(request: SkillSuggestRequest):
    return suggest_skills(
        job_description=request.job_description,
        user_skills=request.user_skills,
        taxonomy=_taxonomy,
    )


@app.get("/api/filters/levels")
def filter_levels():
    return {"levels": db_queries.get_filter_levels()}


@app.get("/api/filters/locations")
def filter_locations():
    return {"locations": db_queries.get_filter_locations()}
