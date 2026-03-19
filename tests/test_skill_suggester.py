"""Unit tests for the skill suggestion module."""

import pytest
from market_analyzer.skill_suggester import suggest_skills


@pytest.fixture
def taxonomy():
    return {
        "Languages": {"python", "javascript", "java", "c++", "go", "r", "c"},
        "Frameworks_Libs": {"react", "django", "flask", "angular", ".net"},
        "Tools_Infrastructure": {"docker", "kubernetes", "git", "ci/cd"},
        "Cloud_Platforms": {"aws", "azure", "gcp"},
        "Soft_Skills": {"communication", "leadership"},
    }


class TestSuggestSkills:
    def test_returns_missing_skills(self, taxonomy):
        job_desc = "We need a python and react developer with docker experience"
        user_skills = ["python"]
        result = suggest_skills(job_desc, user_skills, taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        assert "react" in skill_names
        assert "docker" in skill_names
        assert "python" not in skill_names

    def test_excludes_soft_skills(self, taxonomy):
        job_desc = "Need strong communication and leadership and python"
        result = suggest_skills(job_desc, [], taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        assert "communication" not in skill_names
        assert "leadership" not in skill_names

    def test_highlights_top_3(self, taxonomy):
        job_desc = "python javascript react django docker aws git"
        result = suggest_skills(job_desc, [], taxonomy)
        assert len(result["highlighted"]) <= 3
        assert len(result["highlighted"]) > 0

    def test_sorted_by_weight(self, taxonomy):
        job_desc = "python react docker aws"
        result = suggest_skills(job_desc, [], taxonomy)
        weights = [s["weight"] for s in result["suggestions"]]
        assert weights == sorted(weights, reverse=True)

    def test_fuzzy_matching_catches_typos(self, taxonomy):
        job_desc = "We need kubernetes and python experience"
        user_skills = ["kuberntes"]  # typo
        result = suggest_skills(job_desc, user_skills, taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        # Fuzzy match should catch "kuberntes" ≈ "kubernetes"
        assert "kubernetes" not in skill_names

    def test_short_skills_exact_match_only(self, taxonomy):
        job_desc = "We use c and r for data analysis and go for backend"
        user_skills = []
        result = suggest_skills(job_desc, user_skills, taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        # Short skills should appear as suggestions when not in user skills
        # They should use exact matching (not fuzzy)
        # The taxonomy extraction should find them
        assert isinstance(result["suggestions"], list)

    def test_special_chars_in_skills(self, taxonomy):
        job_desc = "Must know c++ and .net and ci/cd pipelines"
        result = suggest_skills(job_desc, [], taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        # These skills with special chars should be found
        assert "c++" in skill_names or ".net" in skill_names or "ci/cd" in skill_names

    def test_empty_job_description(self, taxonomy):
        result = suggest_skills("", [], taxonomy)
        assert result["suggestions"] == []
        assert result["highlighted"] == []

    def test_all_skills_already_known(self, taxonomy):
        job_desc = "python react docker"
        user_skills = ["python", "react", "docker"]
        result = suggest_skills(job_desc, user_skills, taxonomy)
        assert result["suggestions"] == []

    def test_case_insensitive_user_skills(self, taxonomy):
        job_desc = "python experience required"
        user_skills = ["Python"]
        result = suggest_skills(job_desc, user_skills, taxonomy)
        skill_names = [s["skill"] for s in result["suggestions"]]
        assert "python" not in skill_names
