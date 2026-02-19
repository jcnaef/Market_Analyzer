import sqlite3

class SkillRecommender:
    def __init__(self, db_path):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM skills")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"Skill engine ready. {count} skills in database.")

    def get_skill_recommendations(self, skill_name, limit=10):
        skill_lower = skill_name.lower()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check skill exists
        cursor.execute("SELECT id FROM skills WHERE LOWER(name) = ? LIMIT 1", (skill_lower,))
        if cursor.fetchone() is None:
            conn.close()
            return None

        # Co-occurrence with conditional probability score
        cursor.execute("""
            SELECT s2.name,
                   CAST(COUNT(*) AS FLOAT) / (
                       SELECT COUNT(*) FROM job_skills js_inner
                       JOIN skills s_inner ON js_inner.skill_id = s_inner.id
                       WHERE LOWER(s_inner.name) = ?
                   ) AS score
            FROM job_skills js1
            JOIN job_skills js2 ON js1.job_id = js2.job_id
            JOIN skills s1 ON js1.skill_id = s1.id
            JOIN skills s2 ON js2.skill_id = s2.id
            WHERE LOWER(s1.name) = ? AND LOWER(s2.name) != ?
            GROUP BY s2.id
            ORDER BY score DESC
            LIMIT ?
        """, (skill_lower, skill_lower, skill_lower, limit))

        results = [{"skill": row["name"], "score": round(row["score"], 2)}
                   for row in cursor.fetchall()]
        conn.close()
        return results
