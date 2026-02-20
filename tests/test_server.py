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
