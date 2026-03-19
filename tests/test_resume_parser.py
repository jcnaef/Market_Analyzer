"""Unit tests for the rule-based resume parser."""

import pytest
from market_analyzer.resume_parser import parse_resume, _is_linkedin_pdf


# --- Sample resume texts ---

FULL_RESUME = """John Smith
john.smith@email.com
(555) 123-4567
linkedin.com/in/johnsmith

Summary
Experienced software engineer with 8 years building scalable web applications
and distributed systems.

Experience
Senior Software Engineer at Google    Jan 2021 - Present
• Led migration of monolithic service to microservices architecture
• Reduced API latency by 40% through caching layer implementation
• Mentored team of 4 junior engineers

Software Engineer, Amazon    Jun 2018 - Dec 2020
• Built real-time inventory tracking system processing 10M events/day
• Implemented CI/CD pipeline reducing deployment time by 60%

Education
University of Washington    2014 - 2018
B.S. Computer Science
GPA: 3.8

Skills
Python, Java, Go, Kubernetes, Docker, AWS, PostgreSQL, React
"""

MINIMAL_RESUME = """Jane Doe
jane@example.com

Experience
Intern at StartupCo    May 2024 - Aug 2024
• Helped build frontend features
"""

LINKEDIN_RESUME = """John Smith
Software Engineer at Google

Contact
john.smith@email.com
linkedin.com/in/johnsmith

Top Skills
Python
Java
Kubernetes

Summary
Experienced software engineer with 8 years building scalable web applications.

Experience
Google
Senior Software Engineer
Jan 2021 - Present
Led migration of monolithic service to microservices architecture.
Reduced API latency by 40%.

Amazon
Software Engineer
Jun 2018 - Dec 2020
Built real-time inventory tracking system.

Education
University of Washington
2014 - 2018
B.S. Computer Science

Page 1 of 2
"""

GARBAGE_TEXT = """
asdfjkl random noise 12345 !!!
no resume content here whatsoever
just some meaningless text
"""


class TestParseResume:
    """Tests for the main parse_resume function."""

    def test_full_resume_extracts_personal_info(self):
        result = parse_resume(FULL_RESUME)
        pi = result["personal_info"]
        assert pi["name"] == "John Smith"
        assert pi["email"] == "john.smith@email.com"
        assert pi["phone"] == "(555) 123-4567"
        assert "johnsmith" in pi["linkedin"]

    def test_full_resume_extracts_summary(self):
        result = parse_resume(FULL_RESUME)
        assert "software engineer" in result["summary"].lower()
        assert "8 years" in result["summary"]

    def test_full_resume_extracts_experience(self):
        result = parse_resume(FULL_RESUME)
        exp = result["experience"]
        assert len(exp) == 2

        # First entry
        assert "Google" in exp[0]["company"]
        assert "Senior Software Engineer" in exp[0]["title"]
        assert "2021" in exp[0]["start_date"]
        assert len(exp[0]["bullets"]) >= 2

        # Second entry
        assert "Amazon" in exp[1]["company"]
        assert "2018" in exp[1]["start_date"]

    def test_full_resume_extracts_education(self):
        result = parse_resume(FULL_RESUME)
        edu = result["education"]
        assert len(edu) >= 1
        assert "Washington" in edu[0]["institution"]

    def test_full_resume_extracts_skills(self):
        result = parse_resume(FULL_RESUME)
        skills = result["skills"]
        assert len(skills) >= 3
        skill_names_lower = [s.lower() for s in skills]
        assert "python" in skill_names_lower

    def test_full_resume_high_confidence(self):
        result = parse_resume(FULL_RESUME)
        assert result["parse_confidence"] >= 0.8

    def test_minimal_resume_moderate_confidence(self):
        result = parse_resume(MINIMAL_RESUME)
        assert 0.2 <= result["parse_confidence"] <= 0.6
        assert result["personal_info"]["name"] == "Jane Doe"
        assert result["personal_info"]["email"] == "jane@example.com"
        assert len(result["experience"]) >= 1

    def test_empty_text_returns_zero_confidence(self):
        result = parse_resume("")
        assert result["parse_confidence"] == 0.0
        assert result["personal_info"]["name"] == ""
        assert result["experience"] == []
        assert result["education"] == []
        assert result["skills"] == []

    def test_none_text_returns_zero_confidence(self):
        result = parse_resume(None)
        assert result["parse_confidence"] == 0.0

    def test_whitespace_only_returns_zero_confidence(self):
        result = parse_resume("   \n\n  \t  ")
        assert result["parse_confidence"] == 0.0

    def test_garbage_text_low_confidence(self):
        result = parse_resume(GARBAGE_TEXT)
        assert result["parse_confidence"] <= 0.2


class TestLinkedInDetection:
    """Tests for LinkedIn PDF detection and parsing."""

    def test_linkedin_pdf_detected(self):
        assert _is_linkedin_pdf(LINKEDIN_RESUME) is True

    def test_regular_resume_not_linkedin(self):
        assert _is_linkedin_pdf(FULL_RESUME) is False

    def test_linkedin_parser_extracts_personal_info(self):
        result = parse_resume(LINKEDIN_RESUME)
        pi = result["personal_info"]
        assert pi["name"] == "John Smith"
        assert pi["email"] == "john.smith@email.com"
        assert "johnsmith" in pi["linkedin"]

    def test_linkedin_parser_extracts_skills(self):
        result = parse_resume(LINKEDIN_RESUME)
        skills = result["skills"]
        assert "Python" in skills
        assert "Java" in skills
        assert "Kubernetes" in skills

    def test_linkedin_parser_extracts_experience(self):
        result = parse_resume(LINKEDIN_RESUME)
        exp = result["experience"]
        assert len(exp) >= 2

    def test_linkedin_parser_extracts_education(self):
        result = parse_resume(LINKEDIN_RESUME)
        edu = result["education"]
        assert len(edu) >= 1

    def test_linkedin_high_confidence(self):
        result = parse_resume(LINKEDIN_RESUME)
        assert result["parse_confidence"] >= 0.8


class TestDateExtraction:
    """Tests for date pattern handling in experience/education."""

    def test_month_year_format(self):
        text = """Experience
Software Engineer at Acme    Jan 2020 - Dec 2022
• Did things
"""
        result = parse_resume(text)
        exp = result["experience"]
        assert len(exp) == 1
        assert "2020" in exp[0]["start_date"]
        assert "2022" in exp[0]["end_date"]

    def test_present_end_date(self):
        text = """Experience
Engineer at Corp    Mar 2021 - Present
• Working on stuff
"""
        result = parse_resume(text)
        exp = result["experience"]
        assert len(exp) == 1
        assert "present" in exp[0]["end_date"].lower()

    def test_year_only_format(self):
        text = """Education
MIT    2018 - 2022
B.S. Computer Science
"""
        result = parse_resume(text)
        edu = result["education"]
        assert len(edu) >= 1
        assert "2018" in edu[0]["start_date"]


class TestCompanyTitleSplitting:
    """Tests for company/title parsing from header lines."""

    def test_title_at_company(self):
        text = """Experience
Software Engineer at Google    Jan 2020 - Present
• Built stuff
"""
        result = parse_resume(text)
        assert result["experience"][0]["company"] == "Google"
        assert result["experience"][0]["title"] == "Software Engineer"

    def test_company_pipe_title(self):
        text = """Experience
Google | Software Engineer    Jan 2020 - Present
• Built stuff
"""
        result = parse_resume(text)
        assert result["experience"][0]["company"] == "Google"
        assert result["experience"][0]["title"] == "Software Engineer"


class TestBulletExtraction:
    """Tests for bullet point extraction."""

    def test_dash_bullets(self):
        text = """Experience
Dev at Corp    Jan 2020 - Present
- Built feature A
- Improved performance by 30%
- Led team of 3
"""
        result = parse_resume(text)
        bullets = result["experience"][0]["bullets"]
        assert len(bullets) == 3
        assert "Built feature A" in bullets[0]

    def test_dot_bullets(self):
        text = """Experience
Dev at Corp    Jan 2020 - Present
• Built feature A
• Improved performance
"""
        result = parse_resume(text)
        bullets = result["experience"][0]["bullets"]
        assert len(bullets) == 2
