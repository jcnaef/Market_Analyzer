"""Pure database query functions for the Market Analyzer API."""

import math

import psycopg2
from psycopg2.extras import RealDictCursor

from .db_config import DATABASE_URL


def _get_conn(db_url: str = None) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(db_url or DATABASE_URL)
    return conn


def get_dashboard_stats(db_url: str = None) -> dict:
    """Aggregate stats for the dashboard page.

    Returns total jobs/companies/skills, jobs by level, remote vs onsite,
    top 15 technical skills (excluding Soft_Skills), monthly posting trends,
    and salary overview.
    """
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)

    # Totals
    c.execute("SELECT COUNT(*) AS count FROM jobs")
    total_jobs = c.fetchone()["count"]
    c.execute("SELECT COUNT(*) AS count FROM companies")
    total_companies = c.fetchone()["count"]
    c.execute(
        """SELECT COUNT(*) AS count FROM skills s
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'"""
    )
    total_skills = c.fetchone()["count"]
    c.execute(
        "SELECT COUNT(*) AS count FROM jobs WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL"
    )
    jobs_with_salary = c.fetchone()["count"]

    # Jobs by level
    c.execute(
        "SELECT job_level, COUNT(*) as cnt FROM jobs GROUP BY job_level ORDER BY cnt DESC"
    )
    jobs_by_level = [
        {"level": row["job_level"] or "Not Specified", "count": row["cnt"]}
        for row in c.fetchall()
    ]

    # Remote vs onsite
    c.execute("SELECT COUNT(*) AS count FROM jobs WHERE is_remote = TRUE")
    remote_count = c.fetchone()["count"]
    onsite_count = total_jobs - remote_count

    # Top 15 technical skills (no soft skills)
    c.execute(
        """SELECT s.name, sc.name as cat_name, COUNT(*) as cnt
           FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'
           GROUP BY s.id, s.name, sc.name
           ORDER BY cnt DESC
           LIMIT 15"""
    )
    top_skills = [
        {"skill": row["name"], "category": row["cat_name"], "count": row["cnt"]}
        for row in c.fetchall()
    ]

    # Monthly posting trends
    c.execute(
        """SELECT TO_CHAR(publication_date, 'YYYY-MM') as month, COUNT(*) as cnt
           FROM jobs
           WHERE publication_date IS NOT NULL
           GROUP BY month
           ORDER BY month"""
    )
    monthly_trends = [
        {"month": row["month"], "count": row["cnt"]}
        for row in c.fetchall()
    ]

    # Salary overview
    c.execute(
        """SELECT AVG(salary_min) as avg_min, AVG(salary_max) as avg_max,
                  MIN(salary_min) as min_sal, MAX(salary_max) as max_sal
           FROM jobs
           WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"""
    )
    salary_row = c.fetchone()

    salary_overview = {
        "avg_min": round(float(salary_row["avg_min"]), 2) if salary_row["avg_min"] else None,
        "avg_max": round(float(salary_row["avg_max"]), 2) if salary_row["avg_max"] else None,
        "min_salary": round(float(salary_row["min_sal"]), 2) if salary_row["min_sal"] else None,
        "max_salary": round(float(salary_row["max_sal"]), 2) if salary_row["max_sal"] else None,
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
    db_url: str = None,
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
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)

    where_clauses = []
    params = []

    if level:
        where_clauses.append("j.job_level = %s")
        params.append(level)
    if remote_only:
        where_clauses.append("j.is_remote = TRUE")
    if search:
        where_clauses.append("(j.title ILIKE %s OR c.name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if location:
        where_clauses.append(
            """EXISTS (SELECT 1 FROM job_locations jl
               JOIN locations l on jl.location_id = l.id
               WHERE jl.job_id = j.id and l.city ILIKE %s)"""
        )
        params.append(f"%{location}%")
    if skill:
        where_clauses.append(
            """EXISTS(SELECT 1 FROM job_skills js2
               JOIN skills s2 ON js2.skill_id = s2.id
               WHERE js2.job_id = j.id AND LOWER(s2.name) = LOWER(%s))"""
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
        SELECT COUNT(DISTINCT j.id) AS count
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE {where_sql}
    """
    c.execute(count_sql, params)
    total = c.fetchone()["count"]

    # Fetch page
    offset = (page - 1) * per_page
    query_sql = f"""
        SELECT DISTINCT j.id, j.title, c.name as company, j.salary_min, j.salary_max,
               j.is_remote, j.job_level, j.publication_date, j.job_url
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
    """
    c.execute(query_sql, params + [per_page, offset])
    job_rows = c.fetchall()

    job_ids = [row["id"] for row in job_rows]
    locations_map = {jid: [] for jid in job_ids}
    skills_map = {jid: [] for jid in job_ids}
    if job_ids:
        placeholders = ",".join("%s" for _ in job_ids)

        # Fetch all locations for these specific jobs
        loc_sql = f"""
            SELECT jl.job_id, l.city
            FROM job_locations jl
            JOIN locations l on jl.location_id = l.id
            WHERE jl.job_id IN ({placeholders})
        """
        c.execute(loc_sql, job_ids)
        for row in c.fetchall():
            locations_map[row["job_id"]].append(row["city"])

        skill_sql = f"""
            SELECT js.job_id, s.name, sc.name as cat_name
            FROM job_skills js
            JOIN skills s ON js.skill_id = s.id
            JOIN skill_categories sc on s.category_id = sc.id
            WHERE js.job_id IN ({placeholders}) AND sc.name != 'Soft_Skills'
        """
        c.execute(skill_sql, job_ids)
        for row in c.fetchall():
            skills_map[row["job_id"]].append({
                "name": row["name"],
                "category": row["cat_name"]
                })
    jobs = []
    for row in job_rows:
        job_id = row["id"]
        salary_min = row["salary_min"]
        salary_max = row["salary_max"]
        pub_date = row["publication_date"]
        jobs.append({
            "id": job_id,
            "title": row["title"],
            "company": row["company"],
            "locations": locations_map.get(job_id, []),
            "salary_min": float(salary_min) if salary_min is not None else None,
            "salary_max": float(salary_max) if salary_max is not None else None,
            "is_remote": bool(row["is_remote"]),
            "level": row["job_level"],
            "publication_date": pub_date.isoformat() if pub_date else None,
            "job_url": row["job_url"],
            "skills": skills_map.get(job_id, []),
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
    db_url: str = None, group_by: str = "level", names: list[str] | None = None
) -> dict:
    """Salary statistics grouped by level, location, or skill (technical only).

    Returns box-plot-ready data: min, max, avg_mid, std_dev, avg_min, avg_max.
    When *names* is provided the result is filtered to those names only.
    """
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)

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
            placeholders = ",".join("%s" for _ in names)
            base += f" AND job_level IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY job_level ORDER BY avg_max DESC"
        c.execute(base, params)
        rows = c.fetchall()

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
            placeholders = ",".join("%s" for _ in names)
            base += f" AND l.city IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY l.city HAVING COUNT(*) >= 1 ORDER BY avg_max DESC"
        if not names:
            base += " LIMIT 25"
        c.execute(base, params)
        rows = c.fetchall()

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
            placeholders = ",".join("%s" for _ in names)
            base += f" AND s.name IN ({placeholders})"
            params.extend(names)
        base += " GROUP BY s.id, s.name HAVING COUNT(*) >= 1 ORDER BY avg_max DESC"
        if not names:
            base += " LIMIT 25"
        c.execute(base, params)
        rows = c.fetchall()
    else:
        conn.close()
        return {"error": "Invalid group_by. Use 'level', 'location', or 'skill'."}

    data = []
    for row in rows:
        variance = float(row["variance"]) if row["variance"] and row["variance"] > 0 else 0
        std_dev = math.sqrt(variance) if variance > 0 else 0
        data.append({
            "name": row["name"] or "Not Specified",
            "avg_min": round(float(row["avg_min"]), 2) if row["avg_min"] else None,
            "avg_max": round(float(row["avg_max"]), 2) if row["avg_max"] else None,
            "min_salary": round(float(row["min_salary"]), 2) if row["min_salary"] else None,
            "max_salary": round(float(row["max_salary"]), 2) if row["max_salary"] else None,
            "avg_mid": round(float(row["avg_mid"]), 2) if row["avg_mid"] else None,
            "std_dev": round(std_dev, 2),
            "job_count": row["job_count"],
        })

    conn.close()
    return {"group_by": group_by, "data": data}


def analyze_skill_gap(db_url: str = None, known_skills: list[str] = None) -> dict:
    """Analyze skill gap: coverage, missing high-demand technical skills, recommendations."""
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)

    # Get all technical skills with demand counts
    c.execute(
        """SELECT s.name, COUNT(*) as demand
           FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'
           GROUP BY s.id, s.name
           ORDER BY demand DESC"""
    )
    all_skills = c.fetchall()

    known_lower = {s.lower() for s in (known_skills or [])}
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


def analyze_resume_skills(db_url: str = None, extracted_skills: dict = None) -> dict:
    """Analyze extracted resume skills against market demand."""
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)

    # Flatten all extracted skills
    all_extracted = []
    for category, skills in (extracted_skills or {}).items():
        for skill in skills:
            all_extracted.append({"name": skill, "category": category})

    # Get demand for each extracted skill
    skills_with_demand = []
    for s in all_extracted:
        c.execute(
            """SELECT COUNT(*) as demand
               FROM job_skills js
               JOIN skills sk ON js.skill_id = sk.id
               WHERE LOWER(sk.name) = LOWER(%s)""",
            (s["name"],),
        )
        row = c.fetchone()
        skills_with_demand.append({
            "name": s["name"],
            "category": s["category"],
            "demand": row["demand"],
        })

    # Get top demanded technical skills the resume is missing
    extracted_lower = {s["name"].lower() for s in all_extracted}
    if extracted_lower:
        placeholders = ",".join("%s" for _ in extracted_lower)
        c.execute(
            f"""SELECT s.name, sc.name as category, COUNT(*) as demand
               FROM job_skills js
               JOIN skills s ON js.skill_id = s.id
               JOIN skill_categories sc ON s.category_id = sc.id
               WHERE sc.name != 'Soft_Skills' AND LOWER(s.name) NOT IN ({placeholders})
               GROUP BY s.id, s.name, sc.name
               ORDER BY demand DESC
               LIMIT 15""",
            list(extracted_lower),
        )
    else:
        c.execute(
            """SELECT s.name, sc.name as category, COUNT(*) as demand
               FROM job_skills js
               JOIN skills s ON js.skill_id = s.id
               JOIN skill_categories sc ON s.category_id = sc.id
               WHERE sc.name != 'Soft_Skills'
               GROUP BY s.id, s.name, sc.name
               ORDER BY demand DESC
               LIMIT 15"""
        )
    missing = c.fetchall()

    missing_skills = [
        {"name": r["name"], "category": r["category"], "demand": r["demand"]}
        for r in missing
    ]

    # Calculate readiness score
    c.execute(
        """SELECT COUNT(DISTINCT s.id) AS count FROM job_skills js
           JOIN skills s ON js.skill_id = s.id
           JOIN skill_categories sc ON s.category_id = sc.id
           WHERE sc.name != 'Soft_Skills'"""
    )
    total_top_skills = c.fetchone()["count"]

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


def get_filter_levels(db_url: str = None) -> list[str]:
    """Distinct job levels for dropdowns."""
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        "SELECT DISTINCT job_level FROM jobs WHERE job_level IS NOT NULL ORDER BY job_level"
    )
    rows = c.fetchall()
    conn.close()
    return [row["job_level"] for row in rows]


def get_filter_locations(db_url: str = None) -> list[dict]:
    """Distinct locations with job counts for dropdowns."""
    conn = _get_conn(db_url)
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        """SELECT l.city, COUNT(DISTINCT jl.job_id) as job_count
           FROM locations l
           JOIN job_locations jl ON l.id = jl.location_id
           GROUP BY l.city
           ORDER BY job_count DESC"""
    )
    rows = c.fetchall()
    conn.close()
    return [{"city": row["city"], "count": row["job_count"]} for row in rows]
