"""Rule-based resume parser.

Converts raw resume text into a structured dict matching ResumeSchema,
plus a parse_confidence score (0.0–1.0).
"""

import re
from .cleaner import extract_skills_from_text, load_skills

# --- Section heading patterns ---

_SECTION_KEYWORDS = {
    "personal_info": [
        r"personal\s*info", r"contact\s*info", r"contact\s*details",
    ],
    "summary": [
        r"summary", r"objective", r"profile", r"about\s*me", r"professional\s*summary",
    ],
    "experience": [
        r"experience", r"work\s*history", r"employment",
        r"professional\s*experience", r"work\s*experience",
    ],
    "education": [
        r"education", r"academic", r"degrees?", r"certifications?",
    ],
    "skills": [
        r"skills", r"technical\s*skills", r"core\s*competencies",
        r"technologies", r"proficiencies",
    ],
}

# Pre-compile a single regex per section
_SECTION_PATTERNS = {}
for section, kws in _SECTION_KEYWORDS.items():
    combined = "|".join(kws)
    _SECTION_PATTERNS[section] = re.compile(
        rf"^\s*(?:{combined})\s*:?\s*$", re.IGNORECASE
    )

# Date patterns common on resumes
_DATE_PATTERN = re.compile(
    r"("
    # Mon YYYY or Month YYYY
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*\.?\s*\d{4}"
    r"|"
    # MM/YYYY or MM-YYYY
    r"\d{1,2}[/\-]\d{4}"
    r"|"
    # YYYY alone (4-digit year)
    r"\d{4}"
    r"|"
    r"[Pp]resent|[Cc]urrent"
    r")",
    re.IGNORECASE,
)

_DATE_RANGE_PATTERN = re.compile(
    r"("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*\.?\s*\d{4}"
    r"|"
    r"\d{1,2}[/\-]\d{4}"
    r"|"
    r"\d{4}"
    r"|"
    r"[Pp]resent|[Cc]urrent"
    r")"
    r"\s*(?:[-–—]|to)\s*"
    r"("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*\.?\s*\d{4}"
    r"|"
    r"\d{1,2}[/\-]\d{4}"
    r"|"
    r"\d{4}"
    r"|"
    r"[Pp]resent|[Cc]urrent"
    r")",
    re.IGNORECASE,
)

# Email and phone patterns for personal info
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN = re.compile(
    r"(?:\+?1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}"
)
_LINKEDIN_PATTERN = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)

# Bullet prefixes
_BULLET_RE = re.compile(r"^\s*[•\-\*\u2022\u2023\u25E6\u2043\u2219]\s*")

# LinkedIn PDF detection
_LINKEDIN_MARKERS = [
    "linkedin.com",
    "Page 1 of",
    "Contact",
    "Top Skills",
    "Experience",
]


def _is_linkedin_pdf(text: str) -> bool:
    """Detect if text was extracted from a LinkedIn PDF export."""
    score = sum(1 for marker in _LINKEDIN_MARKERS if marker.lower() in text.lower())
    return score >= 3


def _detect_sections(lines: list[str]) -> dict[str, list[str]]:
    """Split lines into named sections based on heading detection."""
    sections: dict[str, list[str]] = {}
    current_section = "header"  # Lines before any detected heading
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Keep blank lines in current section for paragraph separation
            if current_section in sections:
                sections[current_section].append("")
            continue

        matched = False
        for section_name, pattern in _SECTION_PATTERNS.items():
            if pattern.match(stripped):
                current_section = section_name
                if current_section not in sections:
                    sections[current_section] = []
                matched = True
                break

        if not matched:
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(line)

    return sections


def _extract_personal_info(header_lines: list[str]) -> dict:
    """Extract name, email, phone, linkedin from header lines."""
    info = {"name": "", "email": "", "phone": "", "linkedin": ""}
    text = "\n".join(header_lines)

    email_match = _EMAIL_PATTERN.search(text)
    if email_match:
        info["email"] = email_match.group()

    phone_match = _PHONE_PATTERN.search(text)
    if phone_match:
        info["phone"] = phone_match.group()

    linkedin_match = _LINKEDIN_PATTERN.search(text)
    if linkedin_match:
        info["linkedin"] = linkedin_match.group()

    # Name is typically the first non-empty line that isn't contact info
    for line in header_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are just email/phone/linkedin
        if info["email"] and info["email"] in stripped:
            continue
        if info["phone"] and info["phone"] in stripped:
            continue
        if "linkedin.com" in stripped.lower():
            continue
        # Skip lines that look like addresses
        if re.match(r"^\d+\s", stripped):
            continue
        info["name"] = stripped
        break

    return info


def _extract_bullets(lines: list[str]) -> list[str]:
    """Extract bullet points from a list of lines."""
    bullets = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = _BULLET_RE.sub("", stripped).strip()
        if cleaned:
            bullets.append(cleaned)
    return bullets


def _parse_experience_section(lines: list[str]) -> list[dict]:
    """Parse experience section into structured entries."""
    entries = []
    current_entry = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line has a date range — likely a new entry header
        date_match = _DATE_RANGE_PATTERN.search(stripped)
        if date_match:
            if current_entry:
                entries.append(current_entry)

            # Remove the date range from the line to get company/title
            header_text = _DATE_RANGE_PATTERN.sub("", stripped).strip()
            header_text = re.sub(r"[|,]\s*$", "", header_text).strip()

            # Try to split "Title at Company" or "Title, Company" or "Title | Company"
            company, title = _split_company_title(header_text)

            current_entry = {
                "company": company,
                "title": title,
                "start_date": date_match.group(1).strip(),
                "end_date": date_match.group(2).strip(),
                "bullets": [],
            }
            continue

        # If we have a current entry, this is either a sub-header or bullet
        if current_entry:
            if _BULLET_RE.match(stripped):
                cleaned = _BULLET_RE.sub("", stripped).strip()
                if cleaned:
                    current_entry["bullets"].append(cleaned)
            elif not current_entry["company"] or not current_entry["title"]:
                # Could be a continuation of the header (company/title on next line)
                company, title = _split_company_title(stripped)
                if not current_entry["company"]:
                    current_entry["company"] = company or stripped
                if not current_entry["title"]:
                    current_entry["title"] = title or ""
            else:
                # Treat as a bullet without a prefix
                current_entry["bullets"].append(stripped)
        else:
            # No current entry and no date — might be a title/company line
            # before the date line. Start a tentative entry.
            company, title = _split_company_title(stripped)
            current_entry = {
                "company": company or stripped,
                "title": title or "",
                "start_date": "",
                "end_date": "",
                "bullets": [],
            }

    if current_entry:
        entries.append(current_entry)

    return entries


def _split_company_title(text: str) -> tuple[str, str]:
    """Try to split a header line into (company, title).

    Handles patterns like:
      "Software Engineer at Google"
      "Google | Software Engineer"
      "Software Engineer, Google"
    """
    # "Title at Company"
    at_match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if at_match:
        return at_match.group(2).strip(), at_match.group(1).strip()

    # "Company | Title" or "Title | Company"
    if "|" in text:
        parts = [p.strip() for p in text.split("|", 1)]
        if len(parts) == 2:
            return parts[0], parts[1]

    # "Title, Company" — only if there's a single comma
    if text.count(",") == 1:
        parts = [p.strip() for p in text.split(",", 1)]
        if len(parts) == 2:
            return parts[1], parts[0]

    return text, ""


def _parse_education_section(lines: list[str]) -> list[dict]:
    """Parse education section into structured entries."""
    entries = []
    current_entry = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        date_match = _DATE_RANGE_PATTERN.search(stripped)
        single_date = _DATE_PATTERN.search(stripped) if not date_match else None

        if date_match or single_date:
            if current_entry:
                entries.append(current_entry)

            header_text = stripped
            if date_match:
                header_text = _DATE_RANGE_PATTERN.sub("", header_text).strip()
                start = date_match.group(1).strip()
                end = date_match.group(2).strip()
            else:
                header_text = _DATE_PATTERN.sub("", header_text).strip()
                start = single_date.group(1).strip()
                end = ""

            header_text = re.sub(r"[|,\-–—]\s*$", "", header_text).strip()

            current_entry = {
                "institution": header_text,
                "degree": "",
                "field": "",
                "start_date": start,
                "end_date": end,
                "gpa": "",
            }
            continue

        if current_entry:
            # Check for degree info
            degree_match = re.match(
                r"^(B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?|"
                r"Bachelor|Master|Doctor|Associate|MBA|M\.?Eng\.?)",
                stripped, re.IGNORECASE,
            )
            if degree_match and not current_entry["degree"]:
                # Split "B.S. Computer Science" into degree + field
                rest = stripped[degree_match.end():].strip()
                rest = re.sub(r"^(?:of|in|,)\s*", "", rest, flags=re.IGNORECASE).strip()
                current_entry["degree"] = degree_match.group().strip()
                if rest:
                    current_entry["field"] = rest

            # Check for GPA
            gpa_match = re.search(r"GPA\s*:?\s*([\d.]+)", stripped, re.IGNORECASE)
            if gpa_match:
                current_entry["gpa"] = gpa_match.group(1)

            if not degree_match and not gpa_match and not current_entry["degree"]:
                current_entry["degree"] = stripped
        else:
            # No date found — start entry with institution name
            current_entry = {
                "institution": stripped,
                "degree": "",
                "field": "",
                "start_date": "",
                "end_date": "",
                "gpa": "",
            }

    if current_entry:
        entries.append(current_entry)

    return entries


def _parse_linkedin(text: str) -> dict:
    """Dedicated parser for LinkedIn PDF exports.

    LinkedIn PDFs have a predictable structure:
    - Name at top
    - Headline below name
    - Contact section with email/phone/linkedin
    - "Top Skills" section
    - "Summary" section
    - "Experience" section with entries
    - "Education" section with entries
    """
    lines = text.split("\n")
    sections: dict[str, list[str]] = {}
    current = "header"
    sections[current] = []

    linkedin_headings = {
        "summary": re.compile(r"^\s*Summary\s*$", re.IGNORECASE),
        "experience": re.compile(r"^\s*Experience\s*$", re.IGNORECASE),
        "education": re.compile(r"^\s*Education\s*$", re.IGNORECASE),
        "skills": re.compile(r"^\s*(?:Top Skills|Skills)\s*$", re.IGNORECASE),
        "contact": re.compile(r"^\s*Contact\s*$", re.IGNORECASE),
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current in sections:
                sections[current].append("")
            continue

        matched = False
        for name, pattern in linkedin_headings.items():
            if pattern.match(stripped):
                current = name
                if current not in sections:
                    sections[current] = []
                matched = True
                break
        if not matched:
            if current not in sections:
                sections[current] = []
            sections[current].append(line)

    # Extract personal info from header
    personal_info = _extract_personal_info(sections.get("header", []))

    # Also check contact section
    contact_lines = sections.get("contact", [])
    if contact_lines:
        contact_text = "\n".join(contact_lines)
        if not personal_info["email"]:
            m = _EMAIL_PATTERN.search(contact_text)
            if m:
                personal_info["email"] = m.group()
        if not personal_info["linkedin"]:
            m = _LINKEDIN_PATTERN.search(contact_text)
            if m:
                personal_info["linkedin"] = m.group()

    # Summary
    summary = "\n".join(
        l.strip() for l in sections.get("summary", []) if l.strip()
    )

    # Skills from "Top Skills" section
    skill_lines = [l.strip() for l in sections.get("skills", []) if l.strip()]

    # Experience
    experience = _parse_experience_section(sections.get("experience", []))

    # Education
    education = _parse_education_section(sections.get("education", []))

    found_sections = 0
    if personal_info["name"]:
        found_sections += 1
    if summary:
        found_sections += 1
    if experience:
        found_sections += 1
    if education:
        found_sections += 1
    if skill_lines:
        found_sections += 1

    return {
        "personal_info": personal_info,
        "summary": summary,
        "experience": experience,
        "education": education,
        "skills": skill_lines,
        "parse_confidence": round(found_sections / 5, 2),
    }


def parse_resume(raw_text: str) -> dict:
    """Parse raw resume text into a structured dict.

    Returns:
        A dict with keys: personal_info, summary, experience, education,
        skills, parse_confidence.
    """
    if not raw_text or not raw_text.strip():
        return {
            "personal_info": {"name": "", "email": "", "phone": "", "linkedin": ""},
            "summary": "",
            "experience": [],
            "education": [],
            "skills": [],
            "parse_confidence": 0.0,
        }

    # Use dedicated LinkedIn parser if detected
    if _is_linkedin_pdf(raw_text):
        return _parse_linkedin(raw_text)

    # General resume parsing
    lines = raw_text.split("\n")
    sections = _detect_sections(lines)

    # Personal info from header
    personal_info = _extract_personal_info(sections.get("header", []))

    # Also check personal_info section if it exists
    if "personal_info" in sections:
        pi_data = _extract_personal_info(sections["personal_info"])
        for key in ("name", "email", "phone", "linkedin"):
            if pi_data[key] and not personal_info[key]:
                personal_info[key] = pi_data[key]

    # Summary
    summary_lines = sections.get("summary", [])
    summary = "\n".join(l.strip() for l in summary_lines if l.strip())

    # Experience
    experience = _parse_experience_section(sections.get("experience", []))

    # Education
    education = _parse_education_section(sections.get("education", []))

    # Skills — extract from skills section text + use taxonomy matching
    skills_section_lines = sections.get("skills", [])
    skills = []

    if skills_section_lines:
        skills_text = "\n".join(skills_section_lines)
        # Try comma/pipe/bullet separated lists
        for line in skills_section_lines:
            stripped = line.strip()
            if not stripped:
                continue
            cleaned = _BULLET_RE.sub("", stripped).strip()
            # Split on commas, pipes, semicolons
            parts = re.split(r"[,|;]", cleaned)
            for part in parts:
                part = part.strip()
                if part and len(part) < 50:  # Skip long sentences
                    skills.append(part)

    # If no skills section found, try taxonomy extraction from full text
    if not skills:
        taxonomy = load_skills()
        if taxonomy:
            extracted = extract_skills_from_text(raw_text, taxonomy)
            for category, cat_skills in extracted.items():
                if category != "Soft_Skills":
                    skills.extend(cat_skills)

    # Calculate confidence
    found = 0
    if personal_info["name"]:
        found += 1
    if summary:
        found += 1
    if experience:
        found += 1
    if education:
        found += 1
    if skills:
        found += 1

    return {
        "personal_info": personal_info,
        "summary": summary,
        "experience": experience,
        "education": education,
        "skills": skills,
        "parse_confidence": round(found / 5, 2),
    }
