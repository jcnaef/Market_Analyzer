"""LLM-powered resume bullet tailoring with guardrails."""

import os
import json
import logging
import re

from groq import Groq

from .cleaner import extract_skills_from_text, load_skills

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def _build_prompt(
    original_bullets: list[str],
    job_description: str,
    allowed_additions: list[str],
    experience_title: str = "",
    experience_company: str = "",
) -> str:
    bullets_text = "\n".join(f"- {b}" for b in original_bullets)
    additions_text = ", ".join(allowed_additions) if allowed_additions else "None"
    role_context = ""
    if experience_title or experience_company:
        parts = [p for p in [experience_title, experience_company] if p]
        role_context = f"\nROLE CONTEXT: These bullets are from the candidate's position as {' at '.join(parts)}.\n"

    additions_rule = ""
    if allowed_additions:
        additions_rule = f"""
ALLOWED SKILL ADDITIONS: {additions_text}
You may weave these skills/technologies into the bullets where they fit naturally. Do NOT add any other skills or technologies that are not already in the original bullets or this allowed list."""
    else:
        additions_rule = """
No new skills/technologies were approved for addition. Do NOT introduce skills or technologies that are not already mentioned in the original bullets."""

    return f"""You are a professional resume writer. Rewrite the following resume bullet points so they are more compelling for the target job description.
{role_context}
WHAT YOU SHOULD DO:
- Mirror keywords and phrases from the job description where the candidate's experience supports them.
- Strengthen action verbs and quantify impact where possible (e.g., "managed" → "led", add percentages/numbers if implied).
- Reorder or restructure sentences to lead with the most relevant detail for this role.
- Adjust tone and terminology to match the job description's language.

CONSTRAINTS:
- Keep exactly {len(original_bullets)} bullet points.
- Do not fabricate accomplishments, metrics, or responsibilities the candidate did not have.
- Keep each bullet to 1-2 lines.
{additions_rule}

ORIGINAL BULLETS:
{bullets_text}

JOB DESCRIPTION:
{job_description}

Return ONLY a JSON array of {len(original_bullets)} strings (the rewritten bullets). No other text:"""


def _check_guardrails(
    tailored_bullets: list[str],
    original_bullets: list[str],
    allowed_additions: list[str],
    taxonomy: dict | None = None,
) -> list[str]:
    """Check that tailored output only contains authorized skills.

    Returns a list of warning strings for any unauthorized skills found.
    """
    if taxonomy is None:
        taxonomy = load_skills()
    if not taxonomy:
        return []

    original_text = " ".join(original_bullets)
    tailored_text = " ".join(tailored_bullets)

    original_skills = extract_skills_from_text(original_text, taxonomy)
    tailored_skills = extract_skills_from_text(tailored_text, taxonomy)

    # Flatten to sets
    original_flat = set()
    for cat_skills in original_skills.values():
        original_flat.update(s.lower() for s in cat_skills)

    tailored_flat = set()
    for cat_skills in tailored_skills.values():
        tailored_flat.update(s.lower() for s in cat_skills)

    allowed_lower = {s.lower() for s in allowed_additions}

    # New skills in output that weren't in original and aren't allowed
    new_skills = tailored_flat - original_flat - allowed_lower

    warnings = []
    for skill in sorted(new_skills):
        warnings.append(f"Skill Addition Detected: '{skill}'")

    return warnings


def tailor_bullets(
    original_bullets: list[str],
    job_description: str,
    allowed_additions: list[str],
    taxonomy: dict | None = None,
    experience_title: str = "",
    experience_company: str = "",
) -> dict:
    """Tailor resume bullets using LLM with guardrail checks.

    Returns:
        {
            "original": [...],
            "tailored": [...],
            "warnings": [...],
        }
    """
    prompt = _build_prompt(
        original_bullets, job_description, allowed_additions,
        experience_title=experience_title, experience_company=experience_company,
    )

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()
    logger.info("LLM raw response: %s", raw)

    # Parse JSON array from response
    try:
        # Handle cases where LLM wraps in markdown code block
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        tailored = json.loads(raw)
        if not isinstance(tailored, list):
            logger.warning("LLM returned non-list JSON: %s", type(tailored))
            tailored = original_bullets
    except (json.JSONDecodeError, IndexError) as e:
        logger.warning("Failed to parse LLM response as JSON: %s — raw: %s", e, raw)
        tailored = original_bullets

    # Strip any bullet prefixes the LLM may have added (e.g. "• ", "- ")
    _bullet_prefix = re.compile(r"^\s*[•\-\*\u2022\u2023\u25E6\u2043\u2219]\s*")
    tailored = [_bullet_prefix.sub("", b).strip() for b in tailored]

    # Ensure same number of bullets
    if len(tailored) != len(original_bullets):
        logger.warning(
            "Bullet count mismatch: expected %d, got %d",
            len(original_bullets), len(tailored),
        )
        tailored = original_bullets

    warnings = _check_guardrails(
        tailored, original_bullets, allowed_additions, taxonomy
    )

    return {
        "original": original_bullets,
        "tailored": tailored,
        "warnings": warnings,
    }
