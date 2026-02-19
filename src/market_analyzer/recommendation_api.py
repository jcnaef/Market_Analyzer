from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
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
csv_file = ROOT_DIR / "processed_jobs.csv"
if os.path.exists(csv_file):
    skill_brain = SkillRecommender(str(csv_file))
    location_brain = LocationSkillRecommender(str(csv_file))
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
