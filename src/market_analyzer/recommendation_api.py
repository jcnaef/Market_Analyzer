import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
# Import both models
from .ai_skill_recommendation import SkillRecommender
from .ai_location_skill_recommendation import LocationSkillRecommender

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

app = FastAPI()

# Allow CORS so your future frontend can talk to this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
db_file = ROOT_DIR / "market_analyzer.db"
if db_file.exists():
    skill_brain = SkillRecommender(str(db_file))
    location_brain = LocationSkillRecommender(str(db_file))
else:
    skill_brain = None
    location_brain = None

@app.get("/")
def home():
    return {"message": "Go to /skill/{skill_name} to see correlations"}

@app.get("/skill/{name}")
def get_skill_matrix(name: str):
    """
    Example: /skill/python
    Returns top 10 correlated skills.
    """
    if not skill_brain:
        raise HTTPException(status_code=500, detail="Server Error: Data file not found")
        
    results = skill_brain.get_skill_recommendations(name)
    
    if results is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found in database")
        
    return {
        "target_skill": name,
        "related_skills": results
    }
@app.get("/location/{city}")
def get_city_stats(city: str):
    """
    Example: /location/Remote or /location/New%20York
    """
    if not location_brain:
        raise HTTPException(status_code=500, detail="location model not loaded")
    results = location_brain.get_location_trends(city)

    if not results:
        raise HTTPException(status_code=404, detail="Location not found")
    return results

@app.get("/skills/autocomplete")
def skills_autocomplete(q: str = "", limit: int = 8):
    """
    Autocomplete endpoint for skills.
    Query param 'q' is the search prefix (required, non-empty).
    Returns matching skill names ordered alphabetically.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    if not skill_brain:
        raise HTTPException(status_code=500, detail="Skill database not available")

    prefix = q.lower() + "%"
    try:
        conn = sqlite3.connect(skill_brain.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM skills WHERE LOWER(name) LIKE LOWER(?) ORDER BY name ASC LIMIT ?",
            (prefix, limit)
        )
        results = cursor.fetchall()
        conn.close()
        suggestions = [row[0] for row in results]
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/locations/autocomplete")
def locations_autocomplete(q: str = "", limit: int = 8):
    """
    Autocomplete endpoint for locations.
    Filters location_brain.known_locations in memory.
    Returns matching location names ordered alphabetically.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    if not location_brain:
        raise HTTPException(status_code=500, detail="Location database not available")

    try:
        matches = [loc for loc in location_brain.known_locations if loc.lower().startswith(q.lower())]
        suggestions = sorted(matches)[:limit]
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering locations: {str(e)}")
