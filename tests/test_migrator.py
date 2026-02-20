"""Tests for DatabaseMigrator helpers in scripts/migrate_to_sqlite.py."""

import sys
import sqlite3
from pathlib import Path
import pytest

# Add project root so we can import from scripts/
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.migrate_to_sqlite import DatabaseMigrator


@pytest.fixture
def migrator(tmp_path):
    """Create a DatabaseMigrator with a fresh temp database."""
    db_file = tmp_path / "mig_test.db"
    m = DatabaseMigrator(db_path=str(db_file), csv_path="/dev/null")
    m.connect()
    m.initialize_schema()
    return m


# ── parse_salary ────────────────────────────────────────────────


class TestParseSalary:
    def test_range(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        lo, hi = m.parse_salary("$90,000 - $120,000")
        assert lo == 90000.0
        assert hi == 120000.0

    def test_single_value(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        lo, hi = m.parse_salary("$75000")
        assert lo == 75000.0
        assert hi is None

    def test_empty_string(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        assert m.parse_salary("") == (None, None)

    def test_none(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        assert m.parse_salary(None) == (None, None)

    def test_garbage(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        assert m.parse_salary("not a salary") == (None, None)


# ── parse_skills_json ──────────────────────────────────────────


class TestParseSkillsJson:
    def test_valid_json(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        result = m.parse_skills_json('{"Languages": ["python"]}')
        assert result == {"Languages": ["python"]}

    def test_single_quoted_json(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        result = m.parse_skills_json("{'Languages': ['python']}")
        assert result == {"Languages": ["python"]}

    def test_empty_string(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        assert m.parse_skills_json("") == {}

    def test_none(self):
        m = DatabaseMigrator.__new__(DatabaseMigrator)
        assert m.parse_skills_json(None) == {}


# ── get_or_create methods ──────────────────────────────────────


class TestGetOrCreate:
    def test_creates_new_skill_category(self, migrator):
        cat_id = migrator.get_or_create_skill_category("Languages")
        assert cat_id is not None
        assert isinstance(cat_id, int)

    def test_returns_cached_category(self, migrator):
        id1 = migrator.get_or_create_skill_category("Languages")
        id2 = migrator.get_or_create_skill_category("Languages")
        assert id1 == id2

    def test_creates_new_skill(self, migrator):
        skill_id = migrator.get_or_create_skill("python", "Languages")
        assert skill_id is not None

    def test_skip_empty_skill(self, migrator):
        assert migrator.get_or_create_skill("", "Languages") is None
        assert migrator.get_or_create_skill("   ", "Languages") is None


# ── import_job ──────────────────────────────────────────────────


class TestImportJob:
    def _make_row(self, **overrides):
        row = {
            "id": "J999",
            "name": "Test Job",
            "company.id": "C999",
            "company.name": "TestCo",
            "company.short_name": "tc",
            "contents": "Job description",
            "clean_description": "Job description",
            "salary": "$80,000 - $100,000",
            "is_remote": "false",
            "publication_date": "2024-01-01",
            "refs.landing_page": "https://example.com",
            "locations": "[]",
            "skills_data": "{}",
        }
        row.update(overrides)
        return row

    def test_valid_row_imports(self, migrator):
        assert migrator.import_job(self._make_row()) is True
        assert migrator.stats["jobs_imported"] == 1

    def test_missing_id_returns_false(self, migrator):
        assert migrator.import_job(self._make_row(id="")) is False

    def test_upsert_existing_job(self, migrator):
        migrator.import_job(self._make_row())
        migrator.conn.commit()
        migrator.import_job(self._make_row())
        assert migrator.stats["jobs_updated"] >= 1

    def test_tracks_errors(self, migrator):
        row = self._make_row(**{"company.id": ""})
        migrator.import_job(row)
        # Missing company should not count as imported
        assert migrator.stats["jobs_imported"] == 0
