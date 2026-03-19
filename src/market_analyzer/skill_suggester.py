"""Suggest missing skills by comparing a job description against user skills."""

from thefuzz import fuzz

from .cleaner import extract_skills_from_text, load_skills

# Minimum length for fuzzy matching — short skills (C, R, Go) require exact match
_FUZZY_MIN_LEN = 4
_FUZZY_THRESHOLD = 80

# Category weights for sorting suggestions (higher = more important)
_CATEGORY_WEIGHTS = {
    "Languages": 5,
    "Frameworks_Libs": 4,
    "Tools_Infrastructure": 3,
    "Data_Science_ML": 3,
    "Databases": 3,
    "Cloud_Platforms": 2,
    "DevOps_Methodologies": 2,
    "Testing": 2,
    "Web_Technologies": 2,
    "Mobile": 2,
    "Operating_Systems": 1,
}


def suggest_skills(
    job_description: str,
    user_skills: list[str],
    taxonomy: dict | None = None,
) -> dict:
    """Extract skills from a job description and return ones the user is missing.

    Returns:
        {
            "suggestions": [{"skill": str, "category": str, "weight": int}, ...],
            "highlighted": [str, str, str],  # top 3 by weight
        }
    """
    if taxonomy is None:
        taxonomy = load_skills()
    if not taxonomy:
        return {"suggestions": [], "highlighted": []}

    # Extract skills from job description using taxonomy
    extracted = extract_skills_from_text(job_description, taxonomy)

    # Build a flat set of job skills with their categories
    job_skills: list[tuple[str, str]] = []
    for category, skills in extracted.items():
        if category == "Soft_Skills":
            continue
        for skill in skills:
            job_skills.append((skill, category))

    # Normalize user skills for comparison
    user_lower = {s.lower() for s in user_skills}

    # Find missing skills
    missing = []
    seen = set()
    for skill, category in job_skills:
        skill_lower = skill.lower()
        if skill_lower in seen:
            continue
        seen.add(skill_lower)

        # Check exact match
        if skill_lower in user_lower:
            continue

        # Check fuzzy match for longer skills
        if len(skill) >= _FUZZY_MIN_LEN:
            fuzzy_match = any(
                fuzz.ratio(skill_lower, u) >= _FUZZY_THRESHOLD
                for u in user_lower
                if len(u) >= _FUZZY_MIN_LEN
            )
            if fuzzy_match:
                continue

        weight = _CATEGORY_WEIGHTS.get(category, 1)
        missing.append({"skill": skill, "category": category, "weight": weight})

    # Sort by weight descending, then alphabetically
    missing.sort(key=lambda x: (-x["weight"], x["skill"]))

    highlighted = [m["skill"] for m in missing[:3]]

    return {"suggestions": missing, "highlighted": highlighted}
