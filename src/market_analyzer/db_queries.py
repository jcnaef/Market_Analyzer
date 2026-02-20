"""Pure database query functions for the Market Analyzer API."""

import math
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_dashboard_stats(db_path: str) -> dict:
    """Aggregate stats for the dashboard page.

    Returns total jobs/companies/skills, jobs by level, remote vs onsite,
    top 15 technical skills (excluding Soft_Skills), monthly posting trends,
    and salary overview.
    """
    conn = _get_conn(db_path)
    c = conn.cursor()

    # Totals
    total_jobs = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    total_companies = c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    total_skills = c.execute(
        """SELECT COUNT(*) FROM skills s
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'"""
    ).fetchone()[0]
    jobs_with_salary = c.execute(
        "SELECT COUNT(*) FROM jobs WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL"
    ).fetchone()[0]

    # Jobs by level
    jobs_by_level = [
        {"level": row["job_level"] or "Not Specified", "count": row["cnt"]}
        for row in c.execute(
            "SELECT job_level, COUNT(*) as cnt FROM jobs GROUP BY job_level ORDER BY cnt DESC"
        ).fetchall()
    ]

    # Remote vs onsite
    remote_count = c.execute("SELECT COUNT(*) FROM jobs WHERE is_remote = 1").fetchone()[0]
    onsite_count = total_jobs - remote_count

    # Top 15 technical skills (no soft skills)
    top_skills = [
        {"skill": row["name"], "category": row["cat_name"], "count": row["cnt"]}
        for row in c.execute(
            """SELECT s.name, sc.name as cat_name, COUNT(*) as cnt
               FROM job_skills js
               JOIN skills s ON js.skill_id = s.id
               JOIN skill_categories sc ON s.category_id = sc.id
               WHERE sc.name != 'Soft_Skills'
               GROUP BY s.id
               ORDER BY cnt DESC
               LIMIT 15"""
        ).fetchall()
    ]

    # Monthly posting trends
    monthly_trends = [
        {"month": row["month"], "count": row["cnt"]}
        for row in c.execute(
            """SELECT strftime('%Y-%m', publication_date) as month, COUNT(*) as cnt
               FROM jobs
               WHERE publication_date IS NOT NULL
               GROUP BY month
               ORDER BY month"""
        ).fetchall()
    ]

    # Salary overview
    salary_row = c.execute(
        """SELECT AVG(salary_min) as avg_min, AVG(salary_max) as avg_max,
                  MIN(salary_min) as min_sal, MAX(salary_max) as max_sal
           FROM jobs
           WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"""
    ).fetchone()

    salary_overview = {
        "avg_min": round(salary_row["avg_min"], 2) if salary_row["avg_min"] else None,
        "avg_max": round(salary_row["avg_max"], 2) if salary_row["avg_max"] else None,
        "min_salary": round(salary_row["min_sal"], 2) if salary_row["min_sal"] else None,
        "max_salary": round(salary_row["max_sal"], 2) if salary_row["max_sal"] else None,
    }

    conn.close()
    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "total_skills": total_skills,
        "jobs_with_salary": jobs_with_salary,
        "jobs_by_level": jobs_by_level,
        "remote_count": remote_count,
        "onsite_count": onsite_count,
        "top_skills": top_skills,
        "monthly_trends": monthly_trends,
        "salary_overview": salary_overview,
    }


def get_jobs(
    db_path: str,
    page: int = 1,
    per_page: int = 20,
    level: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    remote_only: bool = False,
    search: str | None = None,
    sort: str = "date_desc",
) -> dict:
    """Paginated job listings with filters."""
    conn = _get_conn(db_path)
    c = conn.cursor()

    where_clauses = []
    params = []

    if level:
        where_clauses.append("j.job_level = ?")
        params.append(level)
    if remote_only:
        where_clauses.append("j.is_remote = 1")
    if search:
        where_clauses.append("(j.title LIKE ? OR c.name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if location:
        where_clauses.append(
            """j.id IN (SELECT jl.job_id FROM job_locations jl
               JOIN locations l ON jl.location_id = l.id
               WHERE l.city LIKE ?)"""
        )
        params.append(f"%{location}%")
    if skill:
        where_clauses.append(
            """j.id IN (SELECT js2.job_id FROM job_skills js2
               JOIN skills s2 ON js2.skill_id = s2.id
               WHERE LOWER(s2.name) = LOWER(?))"""
        )
        params.append(skill)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    sort_map = {
        "date_desc": "j.publication_date DESC",
        "date_asc": "j.publication_date ASC",
        "salary_desc": "j.salary_max DESC",
        "salary_asc": "j.salary_min ASC",
    }
    order_sql = sort_map.get(sort, "j.publication_date DESC")

    # Count total
    count_sql = f"""
        SELECT COUNT(DISTINCT j.id)
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE {where_sql}
    """
    total = c.execute(count_sql, params).fetchone()[0]

    # Fetch page
    offset = (page - 1) * per_page
    query_sql = f"""
        SELECT DISTINCT j.id, j.title, c.name as company, j.salary_min, j.salary_max,
               j.is_remote, j.job_level, j.publication_date, j.job_url
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """
    rows = c.execute(query_sql, params + [per_page, offset]).fetchall()

    jobs = []
    for row in rows:
        job_id = row["id"]

        # Get locations for this job
        locations = [
            r["city"]
            for r in c.execute(
                """SELECT l.city FROM job_locations jl
                   JOIN locations l ON jl.location_id = l.id
                   WHERE jl.job_id = ?""",
                (job_id,),
            ).fetchall()
        ]

        # Get skills for this job (technical only)
        skills = [
            {"name": r["name"], "category": r["cat_name"]}
            for r in c.execute(
                """SELECT s.name, sc.name as cat_name
                   FROM job_skills js
                   JOIN skills s ON js.skill_id = s.id
                   JOIN skill_categories sc ON s.category_id = sc.id
                   WHERE js.job_id = ? AND sc.name != 'Soft_Skills'""",
                (job_id,),
            ).fetchall()
        ]

        jobs.append({
            "id": job_id,
            "title": row["title"],
            "company": row["company"],
            "locations": locations,
            "salary_min": row["salary_min"],
            "salary_max": row["salary_max"],
            "is_remote": bool(row["is_remote"]),
            "level": row["job_level"],
            "publication_date": row["publication_date"],
            "job_url": row["job_url"],
            "skills": skills,
        })

    conn.close()
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


def get_salary_insights(
    db_path: str, group_by: str = "level", names: list[str] | None = None
) -> dict:
    """Salary statistics grouped by level, location, or skill (technical only).

    Returns box-plot-ready data: min, max, avg_mid, std_dev, avg_min, avg_max.
    When *names* is provided the result is filtered to those names only.
    """
    conn = _get_conn(db_path)
    c = conn.cursor()

    # Build the extra SELECT columns shared by every branch
    stats_cols = """,
        MIN(salary_min) as min_salary,
        MAX(salary_max) as max_salary,
        AVG((salary_min + salary_max) / 2.0) as avg_mid,
        AVG(((salary_min + salary_max) / 2.0) * ((salary_min + salary_max) / 2.0))
          - AVG((salary_min + salary_max) / 2.0) * AVG((salary_min + salary_max) / 2.0) as variance"""

    if group_by == "level":
        base = f"""SELECT job_level as name,
                          AVG(salary_min) as avg_min, AVG(salary_max) as avg_max,
                          COUNT(*) as job_count{stats_cols}
                   FROM jobs
                   WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"""
        params: list = []
        if names:
            placeholders = ",".join("?" for _ in names)
            base += f" AND job_level IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY job_level ORDER BY avg_max DESC"
        rows = c.execute(base, params).fetchall()

    elif group_by == "location":
        base = f"""SELECT l.city as name,
                          AVG(j.salary_min) as avg_min, AVG(j.salary_max) as avg_max,
                          COUNT(*) as job_count{stats_cols.replace('salary_min', 'j.salary_min').replace('salary_max', 'j.salary_max')}
                   FROM jobs j
                   JOIN job_locations jl ON j.id = jl.job_id
                   JOIN locations l ON jl.location_id = l.id
                   WHERE j.salary_min IS NOT NULL AND j.salary_max IS NOT NULL"""
        params = []
        if names:
            placeholders = ",".join("?" for _ in names)
            base += f" AND l.city IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY l.city HAVING job_count >= 1 ORDER BY avg_max DESC"
        if not names:
            base += " LIMIT 25"
        rows = c.execute(base, params).fetchall()

    elif group_by == "skill":
        base = f"""SELECT s.name as name,
                          AVG(j.salary_min) as avg_min, AVG(j.salary_max) as avg_max,
                          COUNT(*) as job_count{stats_cols.replace('salary_min', 'j.salary_min').replace('salary_max', 'j.salary_max')}
                   FROM jobs j
                   JOIN job_skills js ON j.id = js.job_id
                   JOIN skills s ON js.skill_id = s.id
                   JOIN skill_categories sc ON s.category_id = sc.id
                   WHERE j.salary_min IS NOT NULL AND j.salary_max IS NOT NULL
                         AND sc.name != 'Soft_Skills'"""
        params = []
        if names:
            placeholders = ",".join("?" for _ in names)
            base += f" AND s.name IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY s.id HAVING job_count >= 1 ORDER BY avg_max DESC"
        if not names:
            base += " LIMIT 25"
        rows = c.execute(base, params).fetchall()
    else:
        conn.close()
        return {"error": "Invalid group_by. Use 'level', 'location', or 'skill'."}

    data = []
    for row in rows:
        variance = row["variance"] if row["variance"] and row["variance"] > 0 else 0
        std_dev = math.sqrt(variance) if variance > 0 else 0
        data.append({
            "name": row["name"] or "Not Specified",
            "avg_min": round(row["avg_min"], 2) if row["avg_min"] else None,
            "avg_max": round(row["avg_max"], 2) if row["avg_max"] else None,
            "min_salary": round(row["min_salary"], 2) if row["min_salary"] else None,
            "max_salary": round(row["max_salary"], 2) if row["max_salary"] else None,
            "avg_mid": round(row["avg_mid"], 2) if row["avg_mid"] else None,
            "std_dev": round(std_dev, 2),
            "job_count": row["job_count"],
        })

    conn.close()
    return {"group_by": group_by, "data": data}


def analyze_skill_gap(db_path: str, known_skills: list[str]) -> dict:
    """Analyze skill gap: coverage, missing high-demand technical skills, recommendations."""
    conn = _get_conn(db_path)
    c = conn.cursor()

    # Get all technical skills with demand counts
    all_skills = c.execute(
        """SELECT s.name, COUNT(*) as demand
           FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'
           GROUP BY s.id
           ORDER BY demand DESC"""
    ).fetchall()

    known_lower = {s.lower() for s in known_skills}
    total_demand = sum(row["demand"] for row in all_skills)

    known_demand = 0
    known_details = []
    missing_skills = []

    for row in all_skills:
        if row["name"].lower() in known_lower:
            known_demand += row["demand"]
            known_details.append({"skill": row["name"], "demand": row["demand"]})
        else:
            missing_skills.append({"skill": row["name"], "demand": row["demand"]})

    coverage = round((known_demand / total_demand * 100), 1) if total_demand > 0 else 0

    # Top 5 recommendations = highest demand missing skills
    recommendations = [
        {"skill": s["skill"], "demand": s["demand"], "reason": "High demand in job listings"}
        for s in missing_skills[:5]
    ]

    conn.close()
    return {
        "coverage_percent": coverage,
        "known_skills": known_details,
        "missing_skills": missing_skills[:20],
        "recommendations": recommendations,
        "total_technical_skills": len(all_skills),
    }


def analyze_resume_skills(db_path: str, extracted_skills: dict) -> dict:
    """Analyze extracted resume skills against market demand."""
    conn = _get_conn(db_path)
    c = conn.cursor()

    # Flatten all extracted skills
    all_extracted = []
    for category, skills in extracted_skills.items():
        for skill in skills:
            all_extracted.append({"name": skill, "category": category})

    # Get demand for each extracted skill
    skills_with_demand = []
    for s in all_extracted:
        row = c.execute(
            """SELECT COUNT(*) as demand
               FROM job_skills js
               JOIN skills sk ON js.skill_id = sk.id
               WHERE LOWER(sk.name) = LOWER(?)""",
            (s["name"],),
        ).fetchone()
        skills_with_demand.append({
            "name": s["name"],
            "category": s["category"],
            "demand": row["demand"],
        })

    # Get top demanded technical skills the resume is missing
    extracted_lower = {s["name"].lower() for s in all_extracted}
    missing = c.execute(
        """SELECT s.name, sc.name as category, COUNT(*) as demand
           FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills' AND LOWER(s.name) NOT IN ({})
           GROUP BY s.id
           ORDER BY demand DESC
           LIMIT 15""".format(",".join("?" for _ in extracted_lower)),
        list(extracted_lower),
    ).fetchall() if extracted_lower else c.execute(
        """SELECT s.name, sc.name as category, COUNT(*) as demand
           FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'
           GROUP BY s.id
           ORDER BY demand DESC
           LIMIT 15"""
    ).fetchall()

    missing_skills = [
        {"name": r["name"], "category": r["category"], "demand": r["demand"]}
        for r in missing
    ]

    # Calculate readiness score
    total_top_skills = c.execute(
        """SELECT COUNT(DISTINCT s.id) FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'"""
    ).fetchone()[0]

    matched_count = sum(1 for s in skills_with_demand if s["demand"] > 0)
    readiness = round((matched_count / max(total_top_skills, 1)) * 100, 1)
    # Cap at 100
    readiness = min(readiness, 100.0)

    conn.close()
    return {
        "readiness_score": readiness,
        "extracted_skills": skills_with_demand,
        "missing_skills": missing_skills,
        "total_extracted": len(all_extracted),
        "matched_in_market": matched_count,
    }


def get_filter_levels(db_path: str) -> list[str]:
    """Distinct job levels for dropdowns."""
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT DISTINCT job_level FROM jobs WHERE job_level IS NOT NULL ORDER BY job_level"
    ).fetchall()
    conn.close()
    return [row["job_level"] for row in rows]


def get_filter_locations(db_path: str) -> list[dict]:
    """Distinct locations with job counts for dropdowns."""
    conn = _get_conn(db_path)
    rows = conn.execute(
        """SELECT l.city, COUNT(DISTINCT jl.job_id) as job_count
           FROM locations l
           JOIN job_locations jl ON l.id = jl.location_id
           GROUP BY l.city
           ORDER BY job_count DESC"""
    ).fetchall()
    conn.close()
    return [{"city": row["city"], "count": row["job_count"]} for row in rows]
