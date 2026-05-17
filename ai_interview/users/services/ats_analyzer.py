"""ATS resume analysis: scoring, skill matching, suggestions."""

from users.services.skills_data import PREDEFINED_SKILLS
from users.services.text_utils import (
    clean_text,
    extract_keywords_from_jd,
    extract_text_from_file,
)


def extract_skills(text: str) -> set[str]:
    """Match predefined skills present in text."""
    text_lower = text.lower()
    found = set()
    for skill in PREDEFINED_SKILLS:
        if skill in text_lower:
            found.add(skill)
    return found


def calculate_score(
    resume_keywords: set[str],
    jd_keywords: set[str],
    resume_skills: set[str],
    jd_skills: set[str],
    keyword_weight: float = 0.4,
    skill_weight: float = 0.6,
) -> dict:
    """Weighted ATS score from keyword and skill overlap."""
    matched_kw = resume_keywords & jd_keywords
    missing_kw = jd_keywords - resume_keywords
    matched_sk = resume_skills & jd_skills
    missing_sk = jd_skills - resume_skills

    kw_score = (len(matched_kw) / len(jd_keywords) * 100) if jd_keywords else 0
    sk_score = (len(matched_sk) / len(jd_skills) * 100) if jd_skills else 0
    ats_score = round(keyword_weight * kw_score + skill_weight * sk_score, 1)

    return {
        "ats_score": ats_score,
        "keyword_score": round(kw_score, 1),
        "skill_score": round(sk_score, 1),
        "matched_keywords": sorted(matched_kw),
        "missing_keywords": sorted(missing_kw),
        "matched_skills": sorted(matched_sk),
        "missing_skills": sorted(missing_sk),
    }


def build_suggestions(score: float, missing_skills: set[str], missing_keywords: set[str]) -> list[str]:
    suggestions = []
    if missing_skills:
        suggestions.append(
            f"Add these skills to your resume: {', '.join(list(missing_skills)[:8])}."
        )
    if missing_keywords:
        suggestions.append(
            f"Include these keywords from the JD: {', '.join(list(missing_keywords)[:8])}."
        )
    if score < 50:
        suggestions.append("Your resume needs significant alignment with this job description.")
    elif score < 75:
        suggestions.append("Good match — strengthen weak areas with concrete project examples.")
    else:
        suggestions.append("Strong ATS match. Tailor your summary for this specific role.")
    suggestions.append("Use action verbs and quantify achievements (%, $, time saved).")
    return suggestions


def analyze_resume(uploaded_file, job_description: str) -> dict:
    """Full ATS analysis pipeline."""
    if not uploaded_file:
        raise ValueError("No resume file uploaded.")
    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    resume_text = extract_text_from_file(uploaded_file)
    if not resume_text.strip():
        raise ValueError("Could not extract text from resume. Try another file.")

    resume_keywords = clean_text(resume_text)
    jd_keywords = extract_keywords_from_jd(job_description)
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(job_description)

    # Also treat JD skill-like terms as skills for matching
    jd_skills |= extract_skills(job_description)

    result = calculate_score(resume_keywords, jd_keywords, resume_skills, jd_skills)
    result["resume_text_preview"] = resume_text[:2000]
    result["resume_skills"] = sorted(resume_skills)
    result["suggestions"] = build_suggestions(
        result["ats_score"],
        set(result["missing_skills"]),
        set(result["missing_keywords"]),
    )
    return result
