#!/usr/bin/env python3
"""Test key database queries for the recommendation engine"""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(str(ROOT_DIR / "data" / "market_analyzer.db"))
cursor = conn.cursor()

print("\n" + "="*60)
print("🧪 TESTING RECOMMENDATION ENGINE QUERIES")
print("="*60)

# Query 1: Top skills overall
print("\n1️⃣  Top 10 Most In-Demand Skills")
print("-" * 60)
cursor.execute("""
    SELECT s.name, sc.name as category, COUNT(js.job_id) as job_count
    FROM job_skills js
    JOIN skills s ON js.skill_id = s.id
    JOIN skill_categories sc ON s.category_id = sc.id
    GROUP BY s.id
    ORDER BY job_count DESC
    LIMIT 10
""")
for name, category, count in cursor.fetchall():
    print(f"  {name:25} [{category:20}] {count:>3} jobs")

# Query 2: Skills by category
print("\n2️⃣  Skills Distribution by Category")
print("-" * 60)
cursor.execute("""
    SELECT sc.name, COUNT(s.id) as skill_count, COUNT(DISTINCT js.job_id) as jobs_using
    FROM skill_categories sc
    LEFT JOIN skills s ON sc.id = s.category_id
    LEFT JOIN job_skills js ON s.id = js.skill_id
    GROUP BY sc.id
    ORDER BY jobs_using DESC
""")
for category, skills_count, jobs_using in cursor.fetchall():
    print(f"  {category:20} {skills_count:>3} skills, used in {jobs_using:>4} jobs")

# Query 3: Co-occurrence example (skills that appear with react)
print("\n3️⃣  Skills Co-Occurrence with 'react'")
print("-" * 60)
cursor.execute("""
    SELECT s2.name, sc.name as category, COUNT(*) as frequency
    FROM job_skills js1
    JOIN job_skills js2 ON js1.job_id = js2.job_id
    JOIN skills s1 ON js1.skill_id = s1.id
    JOIN skills s2 ON js2.skill_id = s2.id
    JOIN skill_categories sc ON s2.category_id = sc.id
    WHERE LOWER(s1.name) = 'react' AND s2.name != s1.name
    GROUP BY s2.id
    ORDER BY frequency DESC
    LIMIT 10
""")
results = cursor.fetchall()
if results:
    for skill, category, freq in results:
        print(f"  {skill:25} [{category:20}] appears {freq:>3} times with React")
else:
    print("  (react not found in database)")

# Query 4: Jobs by location and remote status
print("\n4️⃣  Jobs by Location")
print("-" * 60)
cursor.execute("""
    SELECT
        CASE WHEN l.is_remote = 1 THEN 'Remote' ELSE l.city END as location,
        COUNT(DISTINCT j.id) as job_count,
        COUNT(DISTINCT j.company_id) as company_count
    FROM jobs j
    JOIN job_locations jl ON j.id = jl.job_id
    JOIN locations l ON jl.location_id = l.id
    GROUP BY l.id
    ORDER BY job_count DESC
""")
for location, job_count, company_count in cursor.fetchall():
    print(f"  {location:25} {job_count:>3} jobs from {company_count:>2} companies")

# Query 5: Top companies by job postings
print("\n5️⃣  Top Companies by Job Postings")
print("-" * 60)
cursor.execute("""
    SELECT c.name, COUNT(j.id) as job_count
    FROM companies c
    JOIN jobs j ON c.id = j.company_id
    GROUP BY c.id
    ORDER BY job_count DESC
    LIMIT 10
""")
for name, count in cursor.fetchall():
    print(f"  {name:40} {count:>2} jobs")

# Query 6: Salary statistics
print("\n6️⃣  Salary Statistics (when available)")
print("-" * 60)
cursor.execute("""
    SELECT
        COUNT(*) as jobs_with_salary,
        ROUND(AVG(salary_min), 0) as avg_min_salary,
        ROUND(AVG(salary_max), 0) as avg_max_salary,
        ROUND(MIN(salary_min), 0) as lowest_min,
        ROUND(MAX(salary_max), 0) as highest_max
    FROM jobs
    WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL
""")
row = cursor.fetchone()
if row[0] > 0:
    print(f"  Jobs with salary info:  {row[0]}")
    print(f"  Average salary range:   ${row[1]:,.0f} - ${row[2]:,.0f}")
    print(f"  Min salary found:       ${row[3]:,.0f}")
    print(f"  Max salary found:       ${row[4]:,.0f}")
else:
    print("  No salary data in database")

# Query 7: Single skill stats
print("\n7️⃣  Skill Analysis Example: 'python'")
print("-" * 60)
cursor.execute("""
    SELECT
        s.name,
        sc.name as category,
        COUNT(DISTINCT j.id) as job_count,
        COUNT(DISTINCT j.company_id) as company_count
    FROM skills s
    JOIN skill_categories sc ON s.category_id = sc.id
    LEFT JOIN job_skills js ON s.id = js.skill_id
    LEFT JOIN jobs j ON js.job_id = j.id
    WHERE LOWER(s.name) = 'python'
    GROUP BY s.id
""")
result = cursor.fetchone()
if result:
    print(f"  Skill:       {result[0]}")
    print(f"  Category:    {result[1]}")
    print(f"  Jobs:        {result[2]}")
    print(f"  Companies:   {result[3]}")

    # Show python co-occurrence
    cursor.execute("""
        SELECT s2.name, COUNT(*) as frequency
        FROM job_skills js1
        JOIN job_skills js2 ON js1.job_id = js2.job_id
        JOIN skills s1 ON js1.skill_id = s1.id
        JOIN skills s2 ON js2.skill_id = s2.id
        WHERE LOWER(s1.name) = 'python' AND s2.name != s1.name
        GROUP BY s2.id
        ORDER BY frequency DESC
        LIMIT 5
    """)
    print(f"  Top 5 skills paired with python:")
    for skill, freq in cursor.fetchall():
        print(f"    - {skill} ({freq}x)")
else:
    print("  python not found in database")

print("\n" + "="*60)
print("✓ All queries executed successfully!")
print("="*60 + "\n")

conn.close()
