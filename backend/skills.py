"""Skill-level résumé ↔ job-description matching (no LLM).

Extracts skills from both texts against a curated lexicon, then reports which
JD skills the candidate covers and which are missing. When local embeddings are
available, a missing skill can still count as covered via a close semantic
neighbour among the résumé's skills; otherwise it's lexical. A signal for the
recruiter, never an auto-decision.
"""

from __future__ import annotations

import re
from typing import Optional

# Curated, lower-cased skill lexicon. Multi-word phrases are matched as phrases.
SKILL_LEXICON = {
    # languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby",
    "scala", "kotlin", "swift", "php", "r", "matlab", "sql", "bash",
    # ml / ds
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "llm", "llms", "large language models", "transformers",
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    "xgboost", "mlops", "data science", "statistics", "reinforcement learning",
    "recommendation systems", "feature engineering", "model deployment",
    # data / infra
    "spark", "hadoop", "kafka", "airflow", "snowflake", "bigquery", "redshift",
    "etl", "data engineering", "data pipelines", "postgres", "mongodb", "redis",
    # cloud / devops
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd", "linux",
    "microservices", "rest", "graphql", "git",
    # web
    "react", "next.js", "node.js", "django", "flask", "fastapi", "html", "css",
    # soft / role
    "leadership", "communication", "agile", "scrum", "stakeholder management",
    "product management", "project management", "mentoring",
}

# Longest phrases first so "machine learning" matches before "learning".
_LEXICON_SORTED = sorted(SKILL_LEXICON, key=lambda s: -len(s))


def extract_skills(text: str) -> set[str]:
    t = " " + (text or "").lower() + " "
    found: set[str] = set()
    for skill in _LEXICON_SORTED:
        # word-ish boundary match that tolerates +, #, ., - inside skill tokens
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pattern, t):
            found.add(skill)
    return found


def _semantic_cover(missing: set[str], resume_skills: set[str]) -> set[str]:
    """Use embeddings (if available) to mark a missing skill covered by a close
    résumé skill. Returns the subset of `missing` that is semantically covered."""
    try:
        from dedup import cosine, embed
    except Exception:
        return set()
    covered = set()
    resume_vecs = {}
    for rs in resume_skills:
        v = embed(rs)
        if v is not None:
            resume_vecs[rs] = v
    if not resume_vecs:
        return set()
    for m in missing:
        vm = embed(m)
        if vm is None:
            continue
        if any(cosine(vm, rv) >= 0.72 for rv in resume_vecs.values()):
            covered.add(m)
    return covered


def skill_match(resume_text: str, jd_text: str) -> dict:
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    if not jd_skills:
        return {"coverage": None, "matched": [], "missing": []}

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    # Optionally rescue near-miss skills via embeddings.
    if missing:
        semantically = _semantic_cover(missing, resume_skills)
        matched = matched | semantically
        missing = missing - semantically

    coverage = round(len(matched) / len(jd_skills), 3)
    return {
        "coverage": coverage,
        "matched": sorted(matched),
        "missing": sorted(missing),
    }
