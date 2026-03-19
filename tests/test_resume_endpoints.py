"""Integration tests for resume CRUD endpoints."""

import io
import json
import pytest
from unittest.mock import patch


VALID_RESUME = {
    "personal_info": {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "555-123-4567",
        "linkedin": "linkedin.com/in/johnsmith",
    },
    "summary": "Experienced software engineer.",
    "experience": [
        {
            "company": "Google",
            "title": "Senior Engineer",
            "start_date": "Jan 2021",
            "end_date": "Present",
            "bullets": ["Led migrations", "Reduced latency"],
        }
    ],
    "education": [
        {
            "institution": "MIT",
            "degree": "B.S.",
            "field": "Computer Science",
            "start_date": "2014",
            "end_date": "2018",
            "gpa": "3.8",
        }
    ],
    "skills": ["Python", "Java", "Kubernetes"],
}

FAKE_TOKEN_DECODED = {
    "uid": "test-firebase-uid",
    "email": "testuser@example.com",
    "name": "Test User",
    "picture": "https://example.com/photo.jpg",
}

AUTH_HEADER = {"Authorization": "Bearer fake-test-token"}


@pytest.fixture(autouse=True)
def mock_firebase():
    """Mock Firebase token verification for all tests in this module."""
    with patch("firebase_admin.auth.verify_id_token", return_value=FAKE_TOKEN_DECODED):
        yield


class TestResumeUpload:
    """Tests for POST /api/user/resume/upload."""

    def test_upload_requires_auth(self, test_client):
        file = io.BytesIO(b"dummy content")
        resp = test_client.post(
            "/api/user/resume/upload",
            files={"file": ("resume.pdf", file, "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_rejects_unsupported_format(self, test_client):
        file = io.BytesIO(b"dummy content")
        resp = test_client.post(
            "/api/user/resume/upload",
            files={"file": ("resume.txt", file, "text/plain")},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 400
        assert "PDF and DOCX" in resp.json()["detail"]

    def test_upload_rejects_oversized_file(self, test_client):
        # 6 MB of data
        file = io.BytesIO(b"x" * (6 * 1024 * 1024))
        resp = test_client.post(
            "/api/user/resume/upload",
            files={"file": ("resume.pdf", file, "application/pdf")},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 400
        assert "5 MB" in resp.json()["detail"]

    def test_upload_pdf_returns_parsed_resume(self, test_client):
        """Upload a PDF and verify parsed output structure."""
        resume_text = (
            "John Smith\njohn@example.com\n\nExperience\n"
            "Engineer at Acme    Jan 2020 - Present\n- Built things\n"
        )
        # Mock the text extractor so we don't need a real PDF
        with patch(
            "market_analyzer.server.extract_text_from_file",
            return_value=resume_text,
        ):
            file = io.BytesIO(b"%PDF-1.4 dummy")
            resp = test_client.post(
                "/api/user/resume/upload",
                files={"file": ("resume.pdf", file, "application/pdf")},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "personal_info" in data
        assert "parse_confidence" in data
        assert isinstance(data["experience"], list)
        assert isinstance(data["skills"], list)


class TestResumeSave:
    """Tests for PUT /api/user/resume."""

    def test_save_requires_auth(self, test_client):
        resp = test_client.put("/api/user/resume", json=VALID_RESUME)
        assert resp.status_code == 401

    def test_save_valid_resume(self, test_client):
        resp = test_client.put(
            "/api/user/resume", json=VALID_RESUME, headers=AUTH_HEADER
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_save_updates_has_resume(self, test_client):
        # Save a resume
        test_client.put(
            "/api/user/resume", json=VALID_RESUME, headers=AUTH_HEADER
        )
        # Check user profile
        resp = test_client.get("/api/user/me", headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["has_resume"] is True

    def test_save_upsert_overwrites(self, test_client):
        # Save first version
        test_client.put(
            "/api/user/resume", json=VALID_RESUME, headers=AUTH_HEADER
        )

        # Save updated version
        updated = VALID_RESUME.copy()
        updated["summary"] = "Updated summary"
        test_client.put(
            "/api/user/resume", json=updated, headers=AUTH_HEADER
        )

        # Fetch and verify updated
        resp = test_client.get("/api/user/resume", headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["summary"] == "Updated summary"

    def test_save_malformed_json_returns_422(self, test_client):
        resp = test_client.put(
            "/api/user/resume",
            json={"personal_info": "not a dict"},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 422


class TestResumeGet:
    """Tests for GET /api/user/resume."""

    def test_get_requires_auth(self, test_client):
        resp = test_client.get("/api/user/resume")
        assert resp.status_code == 401

    def test_get_returns_404_when_no_resume(self, test_client):
        resp = test_client.get("/api/user/resume", headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_get_returns_saved_resume(self, test_client):
        # Save first
        test_client.put(
            "/api/user/resume", json=VALID_RESUME, headers=AUTH_HEADER
        )

        # Fetch
        resp = test_client.get("/api/user/resume", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["personal_info"]["name"] == "John Smith"
        assert len(data["experience"]) == 1
        assert data["skills"] == ["Python", "Java", "Kubernetes"]
