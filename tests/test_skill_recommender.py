"""Tests for the SkillRecommender class."""


class TestSkillRecommender:
    def test_returns_recommendations_for_known_skill(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python")
        assert results is not None
        assert len(results) > 0

    def test_returns_none_for_unknown_skill(self, skill_recommender):
        assert skill_recommender.get_skill_recommendations("cobol") is None

    def test_case_insensitive_lookup(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("Python")
        assert results is not None

    def test_excludes_target_skill(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python")
        skill_names = [r["skill"] for r in results]
        assert "python" not in skill_names

    def test_respects_limit(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python", limit=1)
        assert len(results) <= 1

    def test_result_has_skill_and_score_keys(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python")
        for r in results:
            assert "skill" in r
            assert "score" in r

    def test_scores_between_zero_and_one(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python")
        for r in results:
            assert 0.0 <= r["score"] <= 1.0

    def test_results_ordered_descending_by_score(self, skill_recommender):
        results = skill_recommender.get_skill_recommendations("python")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_known_cooccurrence_python_django(self, skill_recommender):
        """python appears in jobs 1 and 3. django appears only in job 1.
        So P(django|python) = 1/2 = 0.5."""
        results = skill_recommender.get_skill_recommendations("python")
        django = next((r for r in results if r["skill"] == "django"), None)
        assert django is not None
        assert django["score"] == 0.5

    def test_known_cooccurrence_python_javascript(self, skill_recommender):
        """python appears in jobs 1 and 3. javascript appears in job 3.
        So P(javascript|python) = 1/2 = 0.5."""
        results = skill_recommender.get_skill_recommendations("python")
        js = next((r for r in results if r["skill"] == "javascript"), None)
        assert js is not None
        assert js["score"] == 0.5
