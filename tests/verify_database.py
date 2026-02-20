#!/usr/bin/env python3
"""Verify SQLite database contents"""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(str(ROOT_DIR / "data" / "market_analyzer.db"))
cursor = conn.cursor()

print("\n📊 Database Verification\n")
print("=" * 50)

# Count records in each table
tables = ["companies", "locations", "skill_categories", "skills", "jobs", "job_skills"]
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table:20} {count:>10,} records")

print("=" * 50)

# Sample data
print("\n📌 Sample Companies:")
cursor.execute("SELECT id, name, short_name FROM companies LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row}")

print("\n📌 Sample Locations:")
cursor.execute("SELECT id, city, state, is_remote FROM locations LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row}")

print("\n📌 Sample Skills (by category):")
cursor.execute("""
    SELECT s.name, sc.name as category FROM skills s
    JOIN skill_categories sc ON s.category_id = sc.id
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]:30} [{row[1]}]")

print("\n📌 Sample Job with Skills:")
cursor.execute("""
    SELECT j.id, j.title, j.company_id, COUNT(js.skill_id) as skill_count
    FROM jobs j
    LEFT JOIN job_skills js ON j.id = js.job_id
    GROUP BY j.id
    LIMIT 1
""")
job = cursor.fetchone()
if job:
    print(f"  Job ID: {job[0]}, Title: {job[1]}, Company: {job[2]}, Skills: {job[3]}")
    cursor.execute("""
        SELECT s.name FROM job_skills js
        JOIN skills s ON js.skill_id = s.id
        WHERE js.job_id = ?
    """, (job[0],))
    print(f"  Skills: {', '.join([row[0] for row in cursor.fetchall()])}")

print("\n✓ Database verification complete!\n")

conn.close()
