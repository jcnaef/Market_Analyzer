"""Debug script: find jobs with suspiciously low salary_min values."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql:///market_analyzer?host=/var/run/postgresql"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 1) Jobs with salary_min = 0
cur.execute("SELECT COUNT(*) FROM jobs WHERE salary_min = 0")
print(f"Jobs with salary_min = 0: {cur.fetchone()[0]}")

# 2) Jobs with salary_min < 1000 (likely hourly rates stored as-is)
cur.execute("""
    SELECT j.id, j.title, c.name AS company, j.salary_min, j.salary_max, j.job_level
    FROM jobs j
    LEFT JOIN companies c ON j.company_id = c.id
    WHERE j.salary_min IS NOT NULL AND j.salary_min < 1000
    ORDER BY j.salary_min
""")
rows = cur.fetchall()
print(f"\nJobs with salary_min < $1,000 (likely bad data): {len(rows)}")
for row in rows:
    print(f"  ID={row[0]}  sal={row[3]}-{row[4]}  level={row[5]}  {row[1]} @ {row[2]}")

# 3) Jobs with NULL salary_min but non-NULL salary_max (or vice versa)
cur.execute("""
    SELECT COUNT(*) FROM jobs
    WHERE (salary_min IS NULL AND salary_max IS NOT NULL)
       OR (salary_min IS NOT NULL AND salary_max IS NULL)
""")
print(f"\nJobs with only one salary bound: {cur.fetchone()[0]}")

# 4) Show the MIN(salary_min) per job_level to see what the chart actually displays
print("\n--- What the chart shows per level ---")
cur.execute("""
    SELECT job_level, MIN(salary_min) as min_sal, MAX(salary_max) as max_sal,
           AVG(salary_min) as avg_min, COUNT(*) as cnt
    FROM jobs
    WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
    GROUP BY job_level
    ORDER BY avg_min DESC
""")
for row in cur.fetchall():
    level, min_sal, max_sal, avg_min, cnt = row
    print(f"  {level or 'Not Specified':20s}  min={min_sal:>10.2f}  max={max_sal:>10.2f}  avg_min={avg_min:>10.2f}  jobs={cnt}")

cur.close()
conn.close()
