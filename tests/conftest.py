"""Shared fixtures for the Market Analyzer test suite."""

import sqlite3
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "data" / "schema.sql"


def _seed_database(conn):
    """Insert deterministic test data into a freshly-created database."""
    c = conn.cursor()

    # 2 companies
    c.execute("INSERT INTO companies (id, muse_company_id, name, short_name) VALUES (1, 'C100', 'Acme Corp', 'acme')")
    c.execute("INSERT INTO companies (id, muse_company_id, name, short_name) VALUES (2, 'C200', 'Globex Inc', 'globex')")

    # 3 locations (New York, San Francisco, Remote)
    c.execute("INSERT INTO locations (id, city, state, country, is_remote) VALUES (1, 'New York', 'NY', 'USA', 0)")
    c.execute("INSERT INTO locations (id, city, state, country, is_remote) VALUES (2, 'San Francisco', 'CA', 'USA', 0)")
    c.execute("INSERT INTO locations (id, city, state, country, is_remote) VALUES (3, 'Remote', NULL, 'USA', 1)")

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
    c.execute("""INSERT INTO jobs (id, muse_job_id, title, company_id, description, clean_description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (1, 'J001', 'Backend Dev', 1, '<p>Build APIs</p>', 'Build APIs',
                90000, 120000, 0, 'Mid Level', '2025-01-15', 'https://example.com/j1', 'open')""")
    c.execute("""INSERT INTO jobs (id, muse_job_id, title, company_id, description, clean_description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (2, 'J002', 'Frontend Dev', 1, '<p>Build UIs</p>', 'Build UIs',
                85000, 115000, 0, 'Entry Level', '2025-02-10', 'https://example.com/j2', 'open')""")
    c.execute("""INSERT INTO jobs (id, muse_job_id, title, company_id, description, clean_description,
                salary_min, salary_max, is_remote, job_level, publication_date, job_url, status)
                VALUES (3, 'J003', 'Fullstack Dev', 2, '<p>Do everything</p>', 'Do everything',
                100000, 140000, 1, 'Senior Level', '2025-03-05', 'https://example.com/j3', 'open')""")

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
def db_path(tmp_path):
    """Create a fresh SQLite database from schema.sql and seed it with test data."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    _seed_database(conn)
    conn.close()
    return str(db_file)


@pytest.fixture
def skill_recommender(db_path):
    """Return a SkillRecommender backed by the test database."""
    from market_analyzer.skill_recommender import SkillRecommender
    return SkillRecommender(db_path)


@pytest.fixture
def location_recommender(db_path):
    """Return a LocationSkillRecommender backed by the test database."""
    from market_analyzer.location_recommender import LocationSkillRecommender
    return LocationSkillRecommender(db_path)


@pytest.fixture
def mock_taxonomy():
    """Small skill taxonomy dict matching skills.json structure."""
    return {
        "Languages": {"python", "javascript", "java", "c++"},
        "Frameworks_Libs": {"react", "django", "flask", "angular"},
        "Tools_Infrastructure": {"docker", "git", "aws", "kubernetes"},
    }


@pytest.fixture
def test_client(db_path, monkeypatch):
    """Patch server globals and return a FastAPI TestClient."""
    from market_analyzer.skill_recommender import SkillRecommender
    from market_analyzer.location_recommender import LocationSkillRecommender
    from market_analyzer import server
    from starlette.testclient import TestClient
    from pathlib import Path

    monkeypatch.setattr(server, "skill_brain", SkillRecommender(db_path))
    monkeypatch.setattr(server, "location_brain", LocationSkillRecommender(db_path))
    monkeypatch.setattr(server, "DB_PATH", db_path)
    monkeypatch.setattr(server, "db_file", Path(db_path))
    return TestClient(server.app)
