"""Tests for collector.py: _JobDBWriter, save_google_jobs_to_db, save_muse_jobs_to_db."""

import pytest
from tests.conftest import TEST_DB_URL


@pytest.fixture
def db_writer(db_url):
    """Return a _JobDBWriter connected to the test database."""
    from market_analyzer.collector import _JobDBWriter
    writer = _JobDBWriter(db_url)
    yield writer
    try:
        writer.conn.close()
    except Exception:
        pass


# ── _JobDBWriter ──────────────────────────────────────────────────


class TestJobDBWriter:
    def test_get_or_create_company_new(self, db_writer):
        cid = db_writer.get_or_create_company("NewCo")
        assert isinstance(cid, int)
        assert db_writer.stats["companies_created"] == 1

    def test_get_or_create_company_cached(self, db_writer):
        id1 = db_writer.get_or_create_company("CacheCo")
        id2 = db_writer.get_or_create_company("CacheCo")
        assert id1 == id2
        assert db_writer.stats["companies_created"] == 1

    def test_get_or_create_company_none(self, db_writer):
        assert db_writer.get_or_create_company(None) is None
        assert db_writer.get_or_create_company("") is None

    def test_get_or_create_location(self, db_writer):
        lid = db_writer.get_or_create_location("TestCity", "TX")
        assert isinstance(lid, int)
        assert db_writer.stats["locations_created"] == 1

    def test_get_or_create_location_cached(self, db_writer):
        id1 = db_writer.get_or_create_location("CacheCity", "CA")
        id2 = db_writer.get_or_create_location("CacheCity", "CA")
        assert id1 == id2
        assert db_writer.stats["locations_created"] == 1

    def test_get_or_create_skill(self, db_writer):
        sid = db_writer.get_or_create_skill("rust", "Languages")
        assert isinstance(sid, int)

    def test_get_or_create_skill_cached(self, db_writer):
        id1 = db_writer.get_or_create_skill("go", "Languages")
        id2 = db_writer.get_or_create_skill("go", "Languages")
        assert id1 == id2

    def test_upsert_job_insert(self, db_writer):
        cid = db_writer.get_or_create_company("UpsertCo")
        job_id = db_writer.upsert_job(
            "TEST-001", "Test Dev", cid, "description",
            80000, 120000, False, "2025-01-01", "https://example.com",
        )
        assert isinstance(job_id, int)
        assert db_writer.stats["jobs_imported"] == 1

    def test_upsert_job_update(self, db_writer):
        cid = db_writer.get_or_create_company("UpsertCo")
        db_writer.upsert_job(
            "TEST-002", "Dev v1", cid, "desc v1",
            None, None, False, None, None,
        )
        db_writer.conn.commit()
        db_writer.upsert_job(
            "TEST-002", "Dev v2", cid, "desc v2",
            90000, 130000, True, None, None,
        )
        assert db_writer.stats["jobs_imported"] == 1
        assert db_writer.stats["jobs_updated"] == 1

    def test_link_location(self, db_writer):
        cid = db_writer.get_or_create_company("LinkCo")
        job_id = db_writer.upsert_job(
            "TEST-LINK", "Link Dev", cid, "desc",
            None, None, False, None, None,
        )
        db_writer.link_location(job_id, "Austin", "TX")
        assert db_writer.stats["locations_created"] >= 1

    def test_link_skills(self, db_writer):
        cid = db_writer.get_or_create_company("SkillCo")
        job_id = db_writer.upsert_job(
            "TEST-SKILL", "Skill Dev", cid, "desc",
            None, None, False, None, None,
        )
        skills = {"Languages": ["python", "go"], "Frameworks_Libs": ["react"]}
        db_writer.link_skills(job_id, skills)
        assert db_writer.stats["skill_links_created"] == 3

    def test_finish(self, db_writer):
        stats = db_writer.finish("Test")
        assert isinstance(stats, dict)
        assert "jobs_imported" in stats


# ── save_google_jobs_to_db ────────────────────────────────────────


class TestSaveGoogleJobsToDB:
    def _make_google_job(self, **overrides):
        job = {
            "job_id": "gj_123",
            "title": "Software Engineer",
            "company_name": "Google",
            "location": "Mountain View, CA",
            "description": "<p>Build things with python and react</p>",
            "detected_extensions": {
                "salary": "$120K - $180K a year",
                "posted_at": "3 days ago",
                "schedule_type": "Full-time",
            },
            "apply_options": [{"link": "https://careers.google.com/j1"}],
        }
        job.update(overrides)
        return job

    def test_imports_single_job(self, db_url):
        from market_analyzer.collector import save_google_jobs_to_db
        stats = save_google_jobs_to_db([self._make_google_job()], db_url=db_url)
        assert stats["jobs_imported"] == 1
        assert stats["errors"] == 0

    def test_upserts_duplicate(self, db_url):
        from market_analyzer.collector import save_google_jobs_to_db
        job = self._make_google_job()
        save_google_jobs_to_db([job], db_url=db_url)
        stats = save_google_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_updated"] == 1

    def test_skips_missing_company(self, db_url):
        from market_analyzer.collector import save_google_jobs_to_db
        job = self._make_google_job(company_name="")
        stats = save_google_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 0
        assert stats["errors"] == 1

    def test_handles_no_salary(self, db_url):
        from market_analyzer.collector import save_google_jobs_to_db
        job = self._make_google_job()
        job["detected_extensions"] = {}
        stats = save_google_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 1

    def test_detects_remote(self, db_url):
        from market_analyzer.collector import save_google_jobs_to_db
        job = self._make_google_job(location="Remote")
        stats = save_google_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 1


# ── save_muse_jobs_to_db ──────────────────────────────────────────


class TestSaveMuseJobsToDB:
    def _make_muse_job(self, **overrides):
        job = {
            "id": 12345,
            "name": "Backend Developer",
            "company": {"name": "MuseCo", "short_name": "mc"},
            "contents": "<p>We need a python developer with django experience. "
                        "Salary $90,000 - $120,000.</p>",
            "locations": [
                {"name": "New York, NY"},
                {"name": "Flexible / Remote"},
            ],
            "publication_date": "2025-03-15",
            "refs": {"landing_page": "https://themuse.com/jobs/12345"},
        }
        job.update(overrides)
        return job

    def test_imports_single_job(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        stats = save_muse_jobs_to_db([self._make_muse_job()], db_url=db_url)
        assert stats["jobs_imported"] == 1
        assert stats["errors"] == 0

    def test_upserts_duplicate(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        job = self._make_muse_job()
        save_muse_jobs_to_db([job], db_url=db_url)
        stats = save_muse_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_updated"] == 1

    def test_skips_missing_company(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        job = self._make_muse_job(company={"name": ""})
        stats = save_muse_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 0
        assert stats["errors"] == 1

    def test_handles_remote_only(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        job = self._make_muse_job(locations=[{"name": "Flexible / Remote"}])
        stats = save_muse_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 1
        assert stats["locations_created"] >= 1

    def test_handles_no_locations(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        job = self._make_muse_job(locations=[])
        stats = save_muse_jobs_to_db([job], db_url=db_url)
        assert stats["jobs_imported"] == 1

    def test_extracts_skills(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        stats = save_muse_jobs_to_db([self._make_muse_job()], db_url=db_url)
        assert stats["skill_links_created"] > 0

    def test_multiple_jobs(self, db_url):
        from market_analyzer.collector import save_muse_jobs_to_db
        jobs = [
            self._make_muse_job(id=1001, name="Job A"),
            self._make_muse_job(id=1002, name="Job B"),
            self._make_muse_job(id=1003, name="Job C"),
        ]
        stats = save_muse_jobs_to_db(jobs, db_url=db_url)
        assert stats["jobs_imported"] == 3
