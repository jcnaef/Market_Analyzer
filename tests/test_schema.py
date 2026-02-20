"""Tests for database schema integrity."""

import sqlite3
import pytest


EXPECTED_TABLES = [
    "companies",
    "locations",
    "skill_categories",
    "skills",
    "jobs",
    "job_locations",
    "job_skills",
]


class TestSchemaIntegrity:
    def test_all_tables_created(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        for t in EXPECTED_TABLES:
            assert t in tables, f"Missing table: {t}"

    def test_unique_constraint_locations(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO locations (city, state, country, is_remote) VALUES ('New York', 'NY', 'USA', 0)"
            )
        conn.close()

    def test_unique_constraint_skills(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO skills (name, category_id) VALUES ('python', 1)")
        conn.close()

    def test_composite_pk_job_skills(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 1)")
        conn.close()

    def test_composite_pk_job_locations(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO job_locations (job_id, location_id) VALUES (1, 1)")
        conn.close()

    def test_expected_indexes_exist(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        expected = [
            "idx_companies_muse_id",
            "idx_locations_city",
            "idx_skills_name",
            "idx_jobs_muse_id",
            "idx_job_skills_skill",
            "idx_job_locations_location",
        ]
        for idx in expected:
            assert idx in indexes, f"Missing index: {idx}"
