"""Tests for database schema integrity."""

import psycopg2
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
    def test_all_tables_created(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        for t in EXPECTED_TABLES:
            assert t in tables, f"Missing table: {t}"

    def test_unique_constraint_locations(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute(
                "INSERT INTO locations (city, state, country) VALUES ('New York', 'NY', 'USA')"
            )
        conn.rollback()
        conn.close()

    def test_unique_constraint_skills(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute("INSERT INTO skills (name, category_id) VALUES ('python', 1)")
        conn.rollback()
        conn.close()

    def test_composite_pk_job_skills(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 1)")
        conn.rollback()
        conn.close()

    def test_composite_pk_job_locations(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute("INSERT INTO job_locations (job_id, location_id) VALUES (1, 1)")
        conn.rollback()
        conn.close()

    def test_expected_indexes_exist(self, db_url):
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        expected = [
            "idx_companies_name",
            "idx_jobs_external_id",
            "idx_locations_city",
            "idx_skills_name",
            "idx_job_skills_skill",
            "idx_job_locations_location",
        ]
        for idx in expected:
            assert idx in indexes, f"Missing index: {idx}"
