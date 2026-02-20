"""Tests for the LocationSkillRecommender class."""


class TestLocationSkillRecommender:
    def test_known_locations_populated(self, location_recommender):
        assert len(location_recommender.known_locations) > 0

    def test_known_locations_includes_remote(self, location_recommender):
        assert "Remote" in location_recommender.known_locations

    def test_known_locations_includes_cities(self, location_recommender):
        assert "New York" in location_recommender.known_locations

    def test_returns_trends_for_exact_match(self, location_recommender):
        result = location_recommender.get_location_trends("New York")
        assert result is not None
        assert result["location"] == "New York"

    def test_returns_trends_for_remote(self, location_recommender):
        result = location_recommender.get_location_trends("Remote")
        assert result is not None
        assert result["location"] == "Remote"

    def test_case_insensitive(self, location_recommender):
        result = location_recommender.get_location_trends("new york")
        assert result is not None

    def test_partial_match(self, location_recommender):
        result = location_recommender.get_location_trends("san")
        assert result is not None
        assert result["location"] == "San Francisco"

    def test_returns_none_for_unknown(self, location_recommender):
        assert location_recommender.get_location_trends("Atlantis") is None

    def test_respects_limit(self, location_recommender):
        result = location_recommender.get_location_trends("New York", limit=1)
        assert len(result["top_skills"]) <= 1

    def test_result_format(self, location_recommender):
        result = location_recommender.get_location_trends("New York")
        assert "location" in result
        assert "top_skills" in result
        for s in result["top_skills"]:
            assert "skill" in s
            assert "count" in s

    def test_results_ordered_by_count_descending(self, location_recommender):
        result = location_recommender.get_location_trends("New York")
        counts = [s["count"] for s in result["top_skills"]]
        assert counts == sorted(counts, reverse=True)

    def test_new_york_skill_counts(self, location_recommender):
        """New York has jobs 1 (python, django) and 2 (javascript, react).
        Each skill should appear in exactly 1 job."""
        result = location_recommender.get_location_trends("New York")
        skills = {s["skill"]: s["count"] for s in result["top_skills"]}
        assert skills["python"] == 1
        assert skills["javascript"] == 1
