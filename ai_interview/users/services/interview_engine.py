"""Structured ~25-minute mock interview engine."""

import re
import uuid
from datetime import timedelta

from django.utils import timezone

from users.services.ai_service import ai_evaluate_answer, ai_generate_followup
from users.services.skills_data import (
    BEHAVIORAL_QUESTIONS,
    CLOSING_QUESTIONS,
    INTRO_QUESTIONS,
    INTERVIEW_ROLES,
    ROLE_KEYWORDS,
    ROLE_TECHNICAL_QUESTIONS,
)

INTERVIEW_DURATION_MINUTES = 25
QUESTIONS_TARGET = 12
PHASES = ("introduction", "technical", "behavioral", "closing")


def _question(text: str, phase: str, difficulty: str = "medium", keywords: list | None = None):
    return {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "phase": phase,
        "difficulty": difficulty,
        "expected_keywords": keywords or [],
    }


def generate_questions(role: str, resume_skills: list | None = None, job_description: str = "") -> list[dict]:
    """Build 10–15 questions across 4 interview phases."""
    if role not in INTERVIEW_ROLES:
        role = "Software Engineer"

    resume_skills = resume_skills or []
    role_kw = ROLE_KEYWORDS.get(role, [])
    skill_pool = list(dict.fromkeys(resume_skills + role_kw))[:6]

    questions = []
    for q in INTRO_QUESTIONS:
        questions.append(_question(q, "introduction", "easy", ["experience", "background", "skills"]))

    tech_bank = ROLE_TECHNICAL_QUESTIONS.get(role, ROLE_TECHNICAL_QUESTIONS["Software Engineer"])
    tech_count = min(8, max(5, QUESTIONS_TARGET - 6))
    for i, (text, diff, kws) in enumerate(tech_bank[:tech_count]):
        extra = [skill_pool[i % len(skill_pool)]] if skill_pool else []
        questions.append(_question(text, "technical", diff, list(kws) + extra))

    if skill_pool and len(questions) < QUESTIONS_TARGET - 3:
        for skill in skill_pool[:2]:
            ai_q = ai_generate_followup(role, skill, "medium")
            if ai_q:
                questions.append(_question(ai_q, "technical", "medium", [skill, role.lower()]))

    for q in BEHAVIORAL_QUESTIONS[:2]:
        questions.append(_question(q, "behavioral", "medium", ["teamwork", "challenge", "communication"]))

    for q in CLOSING_QUESTIONS[:1]:
        questions.append(_question(q, "closing", "easy", ["questions", "role", "team"]))

    return questions[:QUESTIONS_TARGET]


def evaluate_answer(answer: str, expected_keywords: list[str], question: str = "") -> dict:
    """Score answer by keyword relevance; optional AI boost."""
    if not answer or not answer.strip():
        return {
            "score": 0,
            "feedback": "No answer provided.",
            "keywords_found": [],
            "communication_note": "Try to elaborate with specific examples.",
        }

    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    word_count = len(answer.split())
    kw_ratio = len(found) / max(len(expected_keywords), 1)
    length_bonus = min(20, word_count // 5)
    score = min(100, int(kw_ratio * 70 + length_bonus + (10 if word_count > 30 else 0)))

    ai_result = ai_evaluate_answer(question, answer, expected_keywords)
    if ai_result and "score" in ai_result:
        score = int((score + ai_result["score"]) / 2)
        found = list(set(found + ai_result.get("keywords_found", [])))
        feedback = ai_result.get("feedback", "")
    else:
        feedback = (
            "Solid answer with good coverage." if score >= 70
            else "Good start — add more technical detail and examples." if score >= 40
            else "Expand your answer with specific technologies and outcomes."
        )

    return {
        "score": score,
        "feedback": feedback,
        "keywords_found": found,
        "word_count": word_count,
    }


def compute_final_report(answers: list[dict]) -> dict:
    """Aggregate scores into final interview report."""
    if not answers:
        return {
            "overall_score": 0,
            "technical_score": 0,
            "communication_score": 0,
            "strengths": [],
            "weaknesses": ["No answers recorded."],
            "suggestions": ["Complete the full interview for a meaningful report."],
        }

    tech_scores = [a["score"] for a in answers if a.get("phase") == "technical"]
    beh_scores = [a["score"] for a in answers if a.get("phase") in ("behavioral", "introduction")]
    all_scores = [a["score"] for a in answers]

    technical_score = round(sum(tech_scores) / len(tech_scores), 1) if tech_scores else 0
    communication_score = round(sum(beh_scores) / len(beh_scores), 1) if beh_scores else 0
    overall_score = round(sum(all_scores) / len(all_scores), 1)

    strengths, weaknesses = [], []
    high = [a for a in answers if a["score"] >= 75]
    low = [a for a in answers if a["score"] < 50]

    if high:
        strengths.append(f"Strong responses on: {', '.join(a['phase'] for a in high[:3])}.")
    if technical_score >= 70:
        strengths.append("Good technical depth demonstrated.")
    if communication_score >= 70:
        strengths.append("Clear communication and structured answers.")

    if low:
        weaknesses.append("Some answers lacked depth or relevant keywords.")
    if technical_score < 60:
        weaknesses.append("Technical answers need more specifics and examples.")
    if communication_score < 60:
        weaknesses.append("Behavioral answers could use STAR format (Situation, Task, Action, Result).")

    suggestions = [
        "Review role-specific topics and practice 2-minute structured answers.",
        "Record yourself answering common questions to improve clarity.",
        "Study missing keywords from your ATS report and weave them into examples.",
    ]
    if technical_score < 70:
        suggestions.append("Deep-dive one system design or coding pattern per week.")
    if communication_score < 70:
        suggestions.append("Practice STAR method for behavioral questions.")

    return {
        "overall_score": overall_score,
        "technical_score": technical_score,
        "communication_score": communication_score,
        "strengths": strengths or ["Completed the interview — keep practicing!"],
        "weaknesses": weaknesses or ["Minor gaps — focus on consistency."],
        "suggestions": suggestions,
    }


def session_time_remaining(started_at, duration_minutes: int = INTERVIEW_DURATION_MINUTES) -> int:
    """Seconds remaining in interview window."""
    end = started_at + timedelta(minutes=duration_minutes)
    remaining = (end - timezone.now()).total_seconds()
    return max(0, int(remaining))


def progress_percent(current_index: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(100, int((current_index / total) * 100))
