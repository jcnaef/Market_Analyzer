"""Tests for all FastAPI endpoints in server.py."""

import pytest
from market_analyzer import server


class TestHomeEndpoint:
    def test_returns_200(self, test_client):
        resp = test_client.get("/")
        assert resp.status_code == 200

    def test_returns_message(self, test_client):
        data = test_client.get("/").json()
        assert "message" in data


class TestSkillEndpoint:
    def test_200_for_known_skill(self, test_client):
        resp = test_client.get("/skill/python")
        assert resp.status_code == 200

    def test_404_for_unknown_skill(self, test_client):
        resp = test_client.get("/skill/cobol")
        assert resp.status_code == 404

    def test_response_keys(self, test_client):
        data = test_client.get("/skill/python").json()
        assert "target_skill" in data
        assert "related_skills" in data

    def test_500_when_brain_is_none(self, test_client, monkeypatch):
        monkeypatch.setattr(server, "skill_brain", None)
        resp = test_client.get("/skill/python")
        assert resp.status_code == 500


class TestLocationEndpoint:
    def test_200_for_known_location(self, test_client):
        resp = test_client.get("/location/New York")
        assert resp.status_code == 200

    def test_404_for_unknown_location(self, test_client):
        resp = test_client.get("/location/Atlantis")
        assert resp.status_code == 404

    def test_remote_works(self, test_client):
        resp = test_client.get("/location/Remote")
        assert resp.status_code == 200

    def test_500_when_brain_is_none(self, test_client, monkeypatch):
        monkeypatch.setattr(server, "location_brain", None)
        resp = test_client.get("/location/Remote")
        assert resp.status_code == 500


class TestSkillsAutocomplete:
    def test_returns_suggestions(self, test_client):
        data = test_client.get("/skills/autocomplete?q=py").json()
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0

    def test_empty_for_no_match(self, test_client):
        data = test_client.get("/skills/autocomplete?q=zzzzz").json()
        assert data["suggestions"] == []

    def test_400_for_empty_query(self, test_client):
        resp = test_client.get("/skills/autocomplete?q=")
        assert resp.status_code == 400

    def test_respects_limit(self, test_client):
        data = test_client.get("/skills/autocomplete?q=p&limit=1").json()
        assert len(data["suggestions"]) <= 1


class TestLocationsAutocomplete:
    def test_returns_suggestions(self, test_client):
        data = test_client.get("/locations/autocomplete?q=New").json()
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0

    def test_empty_for_no_match(self, test_client):
        data = test_client.get("/locations/autocomplete?q=zzzzz").json()
        assert data["suggestions"] == []

    def test_400_for_empty_query(self, test_client):
        resp = test_client.get("/locations/autocomplete?q=")
        assert resp.status_code == 400


# --- New endpoint tests ---


class TestDashboardStats:
    def test_returns_200(self, test_client):
        resp = test_client.get("/api/dashboard/stats")
        assert resp.status_code == 200

    def test_has_required_keys(self, test_client):
        data = test_client.get("/api/dashboard/stats").json()
        assert "total_jobs" in data
        assert "total_companies" in data
        assert "total_skills" in data
        assert "jobs_with_salary" in data
        assert "jobs_by_level" in data
        assert "remote_count" in data
        assert "onsite_count" in data
        assert "top_skills" in data
        assert "monthly_trends" in data
        assert "salary_overview" in data

    def test_correct_totals(self, test_client):
        data = test_client.get("/api/dashboard/stats").json()
        assert data["total_jobs"] == 3
        assert data["total_companies"] == 2
        assert data["jobs_with_salary"] == 3

    def test_top_skills_excludes_soft_skills(self, test_client):
        data = test_client.get("/api/dashboard/stats").json()
        skill_names = [s["skill"] for s in data["top_skills"]]
        assert "communication" not in skill_names

    def test_remote_count(self, test_client):
        data = test_client.get("/api/dashboard/stats").json()
        assert data["remote_count"] == 1
        assert data["onsite_count"] == 2

    def test_salary_overview(self, test_client):
        data = test_client.get("/api/dashboard/stats").json()
        sal = data["salary_overview"]
        assert sal["avg_min"] is not None
        assert sal["avg_max"] is not None


class TestJobsEndpoint:
    def test_returns_200(self, test_client):
        resp = test_client.get("/api/jobs")
        assert resp.status_code == 200

    def test_pagination_keys(self, test_client):
        data = test_client.get("/api/jobs").json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

    def test_returns_all_jobs(self, test_client):
        data = test_client.get("/api/jobs").json()
        assert data["total"] == 3

    def test_filter_by_level(self, test_client):
        data = test_client.get("/api/jobs?level=Mid Level").json()
        assert all(j["level"] == "Mid Level" for j in data["jobs"])

    def test_filter_remote_only(self, test_client):
        data = test_client.get("/api/jobs?remote_only=true").json()
        assert all(j["is_remote"] for j in data["jobs"])

    def test_filter_by_search(self, test_client):
        data = test_client.get("/api/jobs?search=Backend").json()
        assert len(data["jobs"]) >= 1
        assert any("Backend" in j["title"] for j in data["jobs"])

    def test_filter_by_skill(self, test_client):
        data = test_client.get("/api/jobs?skill=python").json()
        assert len(data["jobs"]) >= 1

    def test_filter_by_location(self, test_client):
        data = test_client.get("/api/jobs?location=New York").json()
        assert len(data["jobs"]) >= 1

    def test_job_has_url(self, test_client):
        data = test_client.get("/api/jobs").json()
        for job in data["jobs"]:
            assert "job_url" in job

    def test_job_skills_exclude_soft(self, test_client):
        data = test_client.get("/api/jobs").json()
        for job in data["jobs"]:
            for skill in job["skills"]:
                assert skill["category"] != "Soft_Skills"

    def test_pagination_limit(self, test_client):
        data = test_client.get("/api/jobs?per_page=1").json()
        assert len(data["jobs"]) <= 1
        assert data["total_pages"] == 3


class TestSalaryInsights:
    def test_by_level(self, test_client):
        data = test_client.get("/api/salary/insights?group_by=level").json()
        assert data["group_by"] == "level"
        assert len(data["data"]) > 0

    def test_by_location(self, test_client):
        data = test_client.get("/api/salary/insights?group_by=location").json()
        assert data["group_by"] == "location"

    def test_by_skill(self, test_client):
        data = test_client.get("/api/salary/insights?group_by=skill").json()
        assert data["group_by"] == "skill"
        skill_names = [d["name"] for d in data["data"]]
        assert "communication" not in skill_names

    def test_invalid_group_by(self, test_client):
        resp = test_client.get("/api/salary/insights?group_by=invalid")
        assert resp.status_code == 400

    def test_data_shape(self, test_client):
        data = test_client.get("/api/salary/insights?group_by=level").json()
        for row in data["data"]:
            assert "name" in row
            assert "avg_min" in row
            assert "avg_max" in row
            assert "job_count" in row


class TestSkillGapAnalyze:
    def test_returns_200(self, test_client):
        resp = test_client.post("/api/skill-gap/analyze", json={"known_skills": ["python"]})
        assert resp.status_code == 200

    def test_coverage_percent(self, test_client):
        data = test_client.post("/api/skill-gap/analyze", json={"known_skills": ["python"]}).json()
        assert "coverage_percent" in data
        assert 0 <= data["coverage_percent"] <= 100

    def test_known_skills_returned(self, test_client):
        data = test_client.post("/api/skill-gap/analyze", json={"known_skills": ["python"]}).json()
        assert any(s["skill"] == "python" for s in data["known_skills"])

    def test_missing_skills(self, test_client):
        data = test_client.post("/api/skill-gap/analyze", json={"known_skills": ["python"]}).json()
        missing_names = [s["skill"] for s in data["missing_skills"]]
        # python is known, so it shouldn't be missing
        assert "python" not in missing_names

    def test_recommendations(self, test_client):
        data = test_client.post("/api/skill-gap/analyze", json={"known_skills": ["python"]}).json()
        assert len(data["recommendations"]) <= 5

    def test_empty_skills(self, test_client):
        data = test_client.post("/api/skill-gap/analyze", json={"known_skills": []}).json()
        assert data["coverage_percent"] == 0


class TestFilterLevels:
    def test_returns_levels(self, test_client):
        data = test_client.get("/api/filters/levels").json()
        assert "levels" in data
        assert len(data["levels"]) > 0

    def test_levels_are_strings(self, test_client):
        data = test_client.get("/api/filters/levels").json()
        for level in data["levels"]:
            assert isinstance(level, str)


class TestFilterLocations:
    def test_returns_locations(self, test_client):
        data = test_client.get("/api/filters/locations").json()
        assert "locations" in data
        assert len(data["locations"]) > 0

    def test_location_shape(self, test_client):
        data = test_client.get("/api/filters/locations").json()
        for loc in data["locations"]:
            assert "city" in loc
            assert "count" in loc


class TestResumeAnalyze:
    def test_rejects_non_pdf_docx(self, test_client):
        resp = test_client.post(
            "/api/resume/analyze",
            files={"file": ("resume.txt", b"some text", "text/plain")},
        )
        assert resp.status_code == 400
