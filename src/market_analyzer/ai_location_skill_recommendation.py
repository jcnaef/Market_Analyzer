import sqlite3

class LocationSkillRecommender:
    def __init__(self, db_path):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT CASE WHEN is_remote = 1 THEN 'Remote' ELSE city END
            FROM locations
        """)
        self.known_locations = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Location engine ready. {len(self.known_locations)} locations available.")

    def get_location_trends(self, location_name, limit=10):
        """
        Retrieves the most in-demand skills for a specific location or remote positions.

        Matching strategy:
        1. Tries exact match first (user input matches location exactly)
        2. Falls back to partial match (user input contained in location name)

        The SQL query:
        1. Filters jobs by location: either is_remote=1 for "Remote" or exact city match
        2. Joins to skills through job_skills (all skills required for those jobs)
        3. Counts distinct jobs requiring each skill
        4. Returns top skills sorted by frequency
        """
        search = location_name.lower()

        matches = [loc for loc in self.known_locations if loc.lower() == search]
        if not matches:
            matches = [loc for loc in self.known_locations if search in loc.lower()]
        if not matches:
            return None

        target = matches[0]
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.name, COUNT(DISTINCT j.id) AS count
            FROM jobs j
            JOIN job_locations jl ON j.id = jl.job_id
            JOIN locations l ON jl.location_id = l.id
            JOIN job_skills js ON j.id = js.job_id
            JOIN skills s ON js.skill_id = s.id
            WHERE (l.is_remote = 1 AND :loc = 'Remote')
               OR (l.is_remote = 0 AND l.city = :loc)
            GROUP BY s.id
            ORDER BY count DESC
            LIMIT :limit
        """, {"loc": target, "limit": limit})

        top_skills = [{"skill": row["name"], "count": row["count"]}
                      for row in cursor.fetchall()]
        conn.close()
        return {"location": target, "top_skills": top_skills}
