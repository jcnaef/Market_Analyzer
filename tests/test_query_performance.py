"""Query performance benchmarks for the Market Analyzer.

Each test calls a real query function against the seeded test database
and asserts it completes within a generous time budget. The actual
elapsed time is printed so you can compare across runs.

Run with:  poetry run pytest tests/test_query_performance.py -v -s
"""

import time
import pytest

from market_analyzer.db_queries import (
    get_dashboard_stats,
    get_jobs,
    get_salary_insights,
    analyze_skill_gap,
    analyze_resume_skills,
    get_filter_levels,
    get_filter_locations,
)
from market_analyzer.skill_recommender import SkillRecommender
from market_analyzer.location_recommender import LocationSkillRecommender


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _time_call(fn, *args, **kwargs):
    """Call *fn* and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, elapsed_ms


def _report(label, elapsed_ms):
    """Print a one-line timing report."""
    print(f"  {label:.<55s} {elapsed_ms:>8.2f} ms")


# Max allowed per query (generous ceiling — these should all be <50 ms on
# the tiny test DB; the budget exists to catch accidental O(n^2) regressions).
BUDGET_MS = 200


# ---------------------------------------------------------------------------
# Dashboard stats (7 queries in one call)
# ---------------------------------------------------------------------------

class TestDashboardPerformance:
    def test_dashboard_stats(self, db_path):
        result, ms = _time_call(get_dashboard_stats, db_path)
        _report("get_dashboard_stats  (7 aggregations)", ms)
        assert ms < BUDGET_MS
        assert result["total_jobs"] == 3
        assert result["total_companies"] == 2
        assert len(result["top_skills"]) > 0

    def test_dashboard_stats_repeated(self, db_path):
        """Second call should benefit from OS page cache."""
        # warm up
        get_dashboard_stats(db_path)
        _, ms = _time_call(get_dashboard_stats, db_path)
        _report("get_dashboard_stats  (warm cache)", ms)
        assert ms < BUDGET_MS


# ---------------------------------------------------------------------------
# Job listing with filters (includes N+1 location/skill subqueries)
# ---------------------------------------------------------------------------

class TestJobListingPerformance:
    def test_jobs_no_filters(self, db_path):
        result, ms = _time_call(get_jobs, db_path)
        _report("get_jobs             (no filters)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 3

    def test_jobs_filter_by_level(self, db_path):
        result, ms = _time_call(get_jobs, db_path, level="Mid Level")
        _report("get_jobs             (filter: level)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 1

    def test_jobs_filter_by_location(self, db_path):
        result, ms = _time_call(get_jobs, db_path, location="New York")
        _report("get_jobs             (filter: location)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 2

    def test_jobs_filter_by_skill(self, db_path):
        result, ms = _time_call(get_jobs, db_path, skill="python")
        _report("get_jobs             (filter: skill)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 2

    def test_jobs_filter_remote_only(self, db_path):
        result, ms = _time_call(get_jobs, db_path, remote_only=True)
        _report("get_jobs             (filter: remote)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 1

    def test_jobs_filter_search_text(self, db_path):
        result, ms = _time_call(get_jobs, db_path, search="Backend")
        _report("get_jobs             (filter: search)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 1

    def test_jobs_combined_filters(self, db_path):
        result, ms = _time_call(
            get_jobs, db_path, location="New York", skill="python"
        )
        _report("get_jobs             (location + skill)", ms)
        assert ms < BUDGET_MS
        assert result["total"] == 1

    def test_jobs_sort_salary_desc(self, db_path):
        result, ms = _time_call(get_jobs, db_path, sort="salary_desc")
        _report("get_jobs             (sort: salary_desc)", ms)
        assert ms < BUDGET_MS
        assert result["jobs"][0]["salary_max"] >= result["jobs"][-1]["salary_max"]


# ---------------------------------------------------------------------------
# Salary insights (heavy aggregations with variance)
# ---------------------------------------------------------------------------

class TestSalaryInsightsPerformance:
    def test_salary_by_level(self, db_path):
        result, ms = _time_call(get_salary_insights, db_path, group_by="level")
        _report("get_salary_insights  (group: level)", ms)
        assert ms < BUDGET_MS
        assert len(result["data"]) > 0

    def test_salary_by_location(self, db_path):
        result, ms = _time_call(get_salary_insights, db_path, group_by="location")
        _report("get_salary_insights  (group: location)", ms)
        assert ms < BUDGET_MS

    def test_salary_by_skill(self, db_path):
        result, ms = _time_call(get_salary_insights, db_path, group_by="skill")
        _report("get_salary_insights  (group: skill)", ms)
        assert ms < BUDGET_MS

    def test_salary_by_level_filtered(self, db_path):
        result, ms = _time_call(
            get_salary_insights, db_path, group_by="level", names=["Mid Level"]
        )
        _report("get_salary_insights  (level filtered)", ms)
        assert ms < BUDGET_MS
        assert len(result["data"]) == 1


# ---------------------------------------------------------------------------
# Skill gap / resume analysis
# ---------------------------------------------------------------------------

class TestSkillGapPerformance:
    def test_skill_gap_analysis(self, db_path):
        known = ["python", "react"]
        result, ms = _time_call(analyze_skill_gap, db_path, known)
        _report("analyze_skill_gap    (2 known skills)", ms)
        assert ms < BUDGET_MS
        assert result["coverage_percent"] > 0

    def test_skill_gap_no_skills(self, db_path):
        result, ms = _time_call(analyze_skill_gap, db_path, [])
        _report("analyze_skill_gap    (0 known skills)", ms)
        assert ms < BUDGET_MS
        assert result["coverage_percent"] == 0

    def test_resume_analysis(self, db_path):
        extracted = {
            "Languages": ["python", "javascript"],
            "Frameworks_Libs": ["react"],
        }
        result, ms = _time_call(analyze_resume_skills, db_path, extracted)
        _report("analyze_resume_skills (3 skills)", ms)
        assert ms < BUDGET_MS
        assert result["matched_in_market"] > 0

    def test_resume_analysis_empty(self, db_path):
        result, ms = _time_call(analyze_resume_skills, db_path, {})
        _report("analyze_resume_skills (empty resume)", ms)
        assert ms < BUDGET_MS


# ---------------------------------------------------------------------------
# Skill recommender (self-join with correlated subquery)
# ---------------------------------------------------------------------------

class TestSkillRecommenderPerformance:
    def test_recommend_from_python(self, skill_recommender):
        start = time.perf_counter()
        result = skill_recommender.get_skill_recommendations("python", limit=5)
        ms = (time.perf_counter() - start) * 1000
        _report("skill_recommendations (python)", ms)
        assert ms < BUDGET_MS
        assert result is not None
        assert len(result) > 0

    def test_recommend_from_react(self, skill_recommender):
        start = time.perf_counter()
        result = skill_recommender.get_skill_recommendations("react", limit=5)
        ms = (time.perf_counter() - start) * 1000
        _report("skill_recommendations (react)", ms)
        assert ms < BUDGET_MS

    def test_recommend_unknown_skill(self, skill_recommender):
        start = time.perf_counter()
        result = skill_recommender.get_skill_recommendations("nonexistent_skill")
        ms = (time.perf_counter() - start) * 1000
        _report("skill_recommendations (unknown)", ms)
        assert ms < BUDGET_MS
        assert result is None


# ---------------------------------------------------------------------------
# Location recommender (4-table JOIN)
# ---------------------------------------------------------------------------

class TestLocationRecommenderPerformance:
    def test_location_new_york(self, location_recommender):
        start = time.perf_counter()
        result = location_recommender.get_location_trends("New York", limit=5)
        ms = (time.perf_counter() - start) * 1000
        _report("location_trends      (New York)", ms)
        assert ms < BUDGET_MS
        assert result is not None

    def test_location_remote(self, location_recommender):
        start = time.perf_counter()
        result = location_recommender.get_location_trends("Remote", limit=5)
        ms = (time.perf_counter() - start) * 1000
        _report("location_trends      (Remote)", ms)
        assert ms < BUDGET_MS

    def test_location_unknown(self, location_recommender):
        start = time.perf_counter()
        result = location_recommender.get_location_trends("Atlantis")
        ms = (time.perf_counter() - start) * 1000
        _report("location_trends      (unknown)", ms)
        assert ms < BUDGET_MS
        assert result is None


# ---------------------------------------------------------------------------
# Filter dropdowns
# ---------------------------------------------------------------------------

class TestFilterPerformance:
    def test_filter_levels(self, db_path):
        result, ms = _time_call(get_filter_levels, db_path)
        _report("get_filter_levels    (DISTINCT)", ms)
        assert ms < BUDGET_MS
        assert len(result) == 3  # Entry, Mid, Senior

    def test_filter_locations(self, db_path):
        result, ms = _time_call(get_filter_locations, db_path)
        _report("get_filter_locations (GROUP BY)", ms)
        assert ms < BUDGET_MS
        assert len(result) > 0
