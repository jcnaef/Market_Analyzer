"""Unit tests for tailoring module and rate limiter."""

import time
import pytest
from unittest.mock import patch, MagicMock

from market_analyzer.tailoring import _build_prompt, _check_guardrails, tailor_bullets
from market_analyzer.rate_limiter import check_rate_limit, reset


@pytest.fixture
def taxonomy():
    return {
        "Languages": {"python", "javascript", "java", "c++"},
        "Frameworks_Libs": {"react", "django", "flask"},
        "Tools_Infrastructure": {"docker", "kubernetes", "git"},
    }


class TestBuildPrompt:
    def test_includes_bullets(self):
        prompt = _build_prompt(
            ["Led team of 5", "Built API"],
            "Need python dev",
            ["python"],
        )
        assert "Led team of 5" in prompt
        assert "Built API" in prompt

    def test_includes_allowed_additions(self):
        prompt = _build_prompt(["Did things"], "job desc", ["python", "docker"])
        assert "python, docker" in prompt

    def test_includes_job_description(self):
        prompt = _build_prompt(["Did things"], "Looking for React expert", [])
        assert "Looking for React expert" in prompt

    def test_no_additions(self):
        prompt = _build_prompt(["Did things"], "job", [])
        assert "No new skills" in prompt


class TestGuardrails:
    def test_no_warnings_when_clean(self, taxonomy):
        original = ["Built APIs with python and django"]
        tailored = ["Developed REST APIs using python and django framework"]
        warnings = _check_guardrails(tailored, original, [], taxonomy)
        assert warnings == []

    def test_warns_on_unauthorized_skill(self, taxonomy):
        original = ["Built APIs"]
        tailored = ["Built APIs using kubernetes and docker"]
        warnings = _check_guardrails(tailored, original, [], taxonomy)
        assert any("kubernetes" in w.lower() for w in warnings)
        assert any("docker" in w.lower() for w in warnings)

    def test_allowed_additions_not_flagged(self, taxonomy):
        original = ["Built APIs"]
        tailored = ["Built APIs using docker"]
        warnings = _check_guardrails(tailored, original, ["docker"], taxonomy)
        assert not any("docker" in w.lower() for w in warnings)

    def test_original_skills_not_flagged(self, taxonomy):
        original = ["Built APIs with python"]
        tailored = ["Developed python REST APIs"]
        warnings = _check_guardrails(tailored, original, [], taxonomy)
        assert warnings == []


class TestTailorBullets:
    def test_returns_original_on_bad_json(self, taxonomy):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("market_analyzer.tailoring._get_client", return_value=mock_client):
            result = tailor_bullets(
                ["Bullet 1", "Bullet 2"],
                "job desc",
                [],
                taxonomy,
            )
        assert result["tailored"] == ["Bullet 1", "Bullet 2"]

    def test_returns_original_on_wrong_count(self, taxonomy):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["Only one bullet"]'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("market_analyzer.tailoring._get_client", return_value=mock_client):
            result = tailor_bullets(
                ["Bullet 1", "Bullet 2"],
                "job desc",
                [],
                taxonomy,
            )
        assert result["tailored"] == ["Bullet 1", "Bullet 2"]

    def test_successful_tailoring(self, taxonomy):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["Tailored bullet 1", "Tailored bullet 2"]'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("market_analyzer.tailoring._get_client", return_value=mock_client):
            result = tailor_bullets(
                ["Bullet 1", "Bullet 2"],
                "job desc",
                [],
                taxonomy,
            )
        assert result["tailored"] == ["Tailored bullet 1", "Tailored bullet 2"]
        assert result["original"] == ["Bullet 1", "Bullet 2"]

    def test_handles_markdown_code_block(self, taxonomy):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n["Tailored 1", "Tailored 2"]\n```'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("market_analyzer.tailoring._get_client", return_value=mock_client):
            result = tailor_bullets(
                ["Bullet 1", "Bullet 2"],
                "job desc",
                [],
                taxonomy,
            )
        assert result["tailored"] == ["Tailored 1", "Tailored 2"]


class TestRateLimiter:
    def setup_method(self):
        reset()

    def test_first_request_allowed(self):
        allowed, msg = check_rate_limit(user_id=1)
        assert allowed is True
        assert msg == ""

    def test_second_request_within_cooldown_blocked(self):
        check_rate_limit(user_id=1)
        allowed, msg = check_rate_limit(user_id=1)
        assert allowed is False
        assert "wait" in msg.lower()

    def test_different_users_independent(self):
        check_rate_limit(user_id=1)
        allowed, msg = check_rate_limit(user_id=2)
        assert allowed is True

    def test_request_allowed_after_cooldown(self):
        from market_analyzer import rate_limiter
        check_rate_limit(user_id=1)
        # Simulate time passing
        rate_limiter._user_last_request[1] -= 15
        allowed, msg = check_rate_limit(user_id=1)
        assert allowed is True
