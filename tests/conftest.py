"""Shared fixtures for the Market Analyzer test suite."""

import psycopg2
from psycopg2.extras import RealDictCursor
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "data" / "schema.sql"

TEST_DB_URL = "postgresql:///market_analyzer_test?host=/var/run/postgresql"


def _seed_database(conn):
    """Insert deterministic test data into a freshly-created database."""
    c = conn.cursor()

    # 2 companies
    c.execute("INSERT INTO companies (id, name, short_name) VALUES (1, 'Acme Corp', 'acme')")
    c.execute("INSERT INTO companies (id, name, short_name) VALUES (2, 'Globex Inc', 'globex')")

    # 3 locations (New York, San Francisco, Remote)
    c.execute("INSERT INTO locations (id, city, state, country) VALUES (1, 'New York', 'NY', 'USA')")
    c.execute("INSERT INTO locations (id, city, state, country) VALUES (2, 'San Francisco', 'CA', 'USA')")
    c.execute("INSERT INTO locations (id, city, state, country) VALUES (3, 'Remote', NULL, 'USA')")

    # 3 skill categories (including Soft_Skills for exclusion testing)
    c.execute("INSERT INTO skill_categories (id, name) VALUES (1, 'Languages')")
    c.execute("INSERT INTO skill_categories (id, name) VALUES (2, 'Frameworks_Libs')")
    c.execute("INSERT INTO skill_categories (id, name) VALUES (3, 'Soft_Skills')")

    # 5 skills (4 technical + 1 soft)
    c.execute("INSERT INTO skills (id, name, category_id) VALUES (1, 'python', 1)")
    c.execute("INSERT INTO skills (id, name, category_id) VALUES (2, 'javascript', 1)")
    c.execute("INSERT INTO skills (id, name, category_id) VALUES (3, 'react', 2)")
    c.execute("INSERT INTO skills (id, name, category_id) VALUES (4, 'django', 2)")
    c.execute("INSERT INTO skills (id, name, category_id) VALUES (5, 'communication', 3)")

    # 3 jobs with salary, job_url, publication_date, job_level
    c.execute("""INSERT INTO jobs (id, external_job_id, title, company_id, description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (1, 'EXT-001', 'Backend Dev', 1, 'Build APIs',
                90000, 120000, FALSE, 'Mid Level', '2025-01-15', 'https://example.com/j1', 'open')""")
    c.execute("""INSERT INTO jobs (id, external_job_id, title, company_id, description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (2, 'EXT-002', 'Frontend Dev', 1, 'Build UIs',
                85000, 115000, FALSE, 'Entry Level', '2025-02-10', 'https://example.com/j2', 'open')""")
    c.execute("""INSERT INTO jobs (id, external_job_id, title, company_id, description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (3, 'EXT-003', 'Fullstack Dev', 2, 'Do everything',
                100000, 140000, TRUE, 'Senior Level', '2025-03-05', 'https://example.com/j3', 'open')""")

    # Reset sequences to avoid conflicts after explicit ID inserts
    c.execute("SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies))")
    c.execute("SELECT setval('locations_id_seq', (SELECT MAX(id) FROM locations))")
    c.execute("SELECT setval('skill_categories_id_seq', (SELECT MAX(id) FROM skill_categories))")
    c.execute("SELECT setval('skills_id_seq', (SELECT MAX(id) FROM skills))")
    c.execute("SELECT setval('jobs_id_seq', (SELECT MAX(id) FROM jobs))")

    # job_locations links
    c.execute("INSERT INTO job_locations (job_id, location_id) VALUES (1, 1)")  # Job1 -> New York
    c.execute("INSERT INTO job_locations (job_id, location_id) VALUES (2, 1)")  # Job2 -> New York
    c.execute("INSERT INTO job_locations (job_id, location_id) VALUES (2, 2)")  # Job2 -> San Francisco
    c.execute("INSERT INTO job_locations (job_id, location_id) VALUES (3, 3)")  # Job3 -> Remote

    # job_skills links
    # Job1 (Backend): python, django, communication
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 1)")
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 4)")
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 5)")
    # Job2 (Frontend): javascript, react
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (2, 2)")
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (2, 3)")
    # Job3 (Fullstack): python, javascript, react
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (3, 1)")
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (3, 2)")
    c.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (3, 3)")

    conn.commit()


@pytest.fixture
def db_url():
    """Create a fresh PostgreSQL test database from schema.sql and seed it with test data.

    Uses the market_analyzer_test database. Drops and recreates all tables each run.
    """
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    c = conn.cursor()

    # Drop all tables to start fresh
    c.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    conn.close()

    # Reconnect without autocommit to run schema + seed
    conn = psycopg2.connect(TEST_DB_URL)
    c = conn.cursor()
    with open(SCHEMA_PATH) as f:
        c.execute(f.read())
    conn.commit()

    _seed_database(conn)
    conn.close()

    return TEST_DB_URL


# Keep db_path as an alias so existing tests work without changes
@pytest.fixture
def db_path(db_url):
    """Alias for db_url for backward compatibility."""
    return db_url


@pytest.fixture
def skill_recommender(db_url):
    """Return a SkillRecommender backed by the test database."""
    from market_analyzer.skill_recommender import SkillRecommender
    return SkillRecommender(db_url)


@pytest.fixture
def location_recommender(db_url):
    """Return a LocationSkillRecommender backed by the test database."""
    from market_analyzer.location_recommender import LocationSkillRecommender
    return LocationSkillRecommender(db_url)


@pytest.fixture
def mock_taxonomy():
    """Small skill taxonomy dict matching skills.json structure."""
    return {
        "Languages": {"python", "javascript", "java", "c++"},
        "Frameworks_Libs": {"react", "django", "flask", "angular"},
        "Tools_Infrastructure": {"docker", "git", "aws", "kubernetes"},
    }


@pytest.fixture
def test_client(db_url, monkeypatch):
    """Patch server globals and return a FastAPI TestClient."""
    from market_analyzer.skill_recommender import SkillRecommender
    from market_analyzer.location_recommender import LocationSkillRecommender
    from market_analyzer import server
    from starlette.testclient import TestClient

    monkeypatch.setattr(server, "skill_brain", SkillRecommender(db_url))
    monkeypatch.setattr(server, "location_brain", LocationSkillRecommender(db_url))
    monkeypatch.setattr(server, "DB_URL", db_url)
    return TestClient(server.app)
