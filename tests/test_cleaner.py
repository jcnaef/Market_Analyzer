"""Tests for NLP / text-processing helpers in cleaner.py."""

from market_analyzer.cleaner import (
    clean_job_text,
    extract_location_info,
    extract_salary,
    extract_skills_from_text,
)


# ── clean_job_text ──────────────────────────────────────────────


class TestCleanJobText:
    def test_strips_html_tags(self):
        assert "Hello world" == clean_job_text("<p>Hello <b>world</b></p>")

    def test_removes_script_and_style_tags(self):
        html = "<script>alert('x')</script><style>.x{}</style><p>Keep this</p>"
        result = clean_job_text(html)
        assert "alert" not in result
        assert "Keep this" in result

    def test_removes_urls(self):
        text = "Visit https://example.com for details"
        assert "https://example.com" not in clean_job_text(text)

    def test_removes_emails(self):
        text = "Contact jobs@example.com for info"
        assert "jobs@example.com" not in clean_job_text(text)

    def test_collapses_whitespace(self):
        text = "too   many     spaces"
        assert "  " not in clean_job_text(text)

    def test_returns_empty_for_none(self):
        assert clean_job_text(None) == ""

    def test_returns_empty_for_non_string(self):
        assert clean_job_text(12345) == ""

    def test_handles_empty_string(self):
        assert clean_job_text("") == ""


# ── extract_location_info ───────────────────────────────────────


class TestExtractLocationInfo:
    def test_single_city(self):
        cities, remote = extract_location_info([{"name": "Denver, CO"}])
        assert cities == ["Denver"]
        assert remote is False

    def test_multiple_cities(self):
        locs = [{"name": "New York, NY"}, {"name": "Seattle, WA"}]
        cities, remote = extract_location_info(locs)
        assert "New York" in cities
        assert "Seattle" in cities

    def test_detects_remote(self):
        locs = [{"name": "Flexible / Remote"}]
        cities, remote = extract_location_info(locs)
        assert remote is True
        assert cities == []

    def test_mixed_city_and_remote(self):
        locs = [{"name": "Remote"}, {"name": "Austin, TX"}]
        cities, remote = extract_location_info(locs)
        assert remote is True
        assert "Austin" in cities

    def test_filters_united_states(self):
        locs = [{"name": "United States"}, {"name": "Chicago, IL"}]
        cities, _ = extract_location_info(locs)
        assert "United States" not in cities
        assert "Chicago" in cities

    def test_empty_list(self):
        cities, remote = extract_location_info([])
        assert cities == []
        assert remote is False

    def test_non_list_input(self):
        cities, remote = extract_location_info("not a list")
        assert cities == []
        assert remote is False


# ── extract_salary ──────────────────────────────────────────────


class TestExtractSalary:
    def test_finds_salary_range(self):
        text = "Salary is $90,000 - $120,000 per year"
        result = extract_salary(text)
        assert result is not None
        assert "$90,000" in result

    def test_returns_none_when_absent(self):
        assert extract_salary("No salary info here") is None

    def test_handles_empty_string(self):
        assert extract_salary("") is None


# ── extract_skills_from_text ────────────────────────────────────


class TestExtractSkillsFromText:
    def test_single_skill(self, mock_taxonomy):
        result = extract_skills_from_text("We use python daily", mock_taxonomy)
        assert "python" in result["Languages"]

    def test_multi_category(self, mock_taxonomy):
        result = extract_skills_from_text("python and react developer", mock_taxonomy)
        assert "python" in result["Languages"]
        assert "react" in result["Frameworks_Libs"]

    def test_bigram_detection(self, mock_taxonomy):
        taxonomy = {"Languages": {"c++"}}
        result = extract_skills_from_text("Experience with c++ required", taxonomy)
        assert "c++" in result["Languages"]

    def test_case_insensitive(self, mock_taxonomy):
        result = extract_skills_from_text("PYTHON and REACT", mock_taxonomy)
        assert "python" in result["Languages"]

    def test_deduplication(self, mock_taxonomy):
        result = extract_skills_from_text("python python python", mock_taxonomy)
        assert result["Languages"].count("python") == 1

    def test_empty_taxonomy_returns_empty(self):
        assert extract_skills_from_text("python developer", {}) == {}
