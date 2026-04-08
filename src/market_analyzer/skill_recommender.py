# Recommends related skills based on co-occurrence patterns in job listings.
# Uses conditional probability to find skills that frequently appear together.

from psycopg2.extras import RealDictCursor

from .db_config import get_db


class SkillRecommender:
    # Connects to the database and verifies the skills table is populated
    def __init__(self, db_url):
        self.db_url = db_url
        with get_db(db_url) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM skills")
            count = cursor.fetchone()[0]
        print(f"Skill engine ready. {count} skills in database.")

    def get_skill_recommendations(self, skill_name, limit=10):
        """
        Finds skills most frequently co-occurring with the target skill using conditional probability.

        The SQL query:
        1. Finds all jobs containing the target skill
        2. Identifies other skills in those same jobs (co-occurrences)
        3. Calculates conditional probability: P(skill2 | target_skill) =
           count(jobs with both) / count(jobs with target)
        4. Returns top skills by probability, sorted descending
        """
        skill_lower = skill_name.lower()
        with get_db(self.db_url) as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT id FROM skills WHERE LOWER(name) = %s LIMIT 1", (skill_lower,))
            if cursor.fetchone() is None:
                return None

            cursor.execute("""
                SELECT s2.name,
                       COUNT(*)::FLOAT / (
                           SELECT COUNT(*) FROM job_skills js_inner
                           JOIN skills s_inner ON js_inner.skill_id = s_inner.id
                           WHERE LOWER(s_inner.name) = %s
                       ) AS score
                FROM job_skills js1
                JOIN job_skills js2 ON js1.job_id = js2.job_id
                JOIN skills s1 ON js1.skill_id = s1.id
                JOIN skills s2 ON js2.skill_id = s2.id
                WHERE LOWER(s1.name) = %s AND LOWER(s2.name) != %s
                GROUP BY s2.id, s2.name
                ORDER BY score DESC
                LIMIT %s
            """, (skill_lower, skill_lower, skill_lower, limit))

            results = [{"skill": row["name"], "score": round(row["score"], 2)}
                       for row in cursor.fetchall()]
            return results
