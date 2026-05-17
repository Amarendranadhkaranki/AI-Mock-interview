"""Optional OpenAI integration for question generation and answer evaluation."""

import json
import os

from django.conf import settings


def _client():
    try:
        from openai import OpenAI
        api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def ai_evaluate_answer(question: str, answer: str, expected_keywords: list[str]) -> dict | None:
    """Use LLM to score an answer; returns None if API unavailable."""
    client = _client()
    if not client:
        return None
    prompt = f"""You are an interview evaluator. Score this answer 0-100.

Question: {question}
Expected topics: {', '.join(expected_keywords)}
Candidate answer: {answer}

Respond ONLY with JSON:
{{"score": number, "feedback": "one sentence", "keywords_found": ["list"]}}"""
    try:
        response = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception:
        return None


def ai_generate_followup(role: str, skill: str, difficulty: str) -> str | None:
    client = _client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{
                "role": "user",
                "content": f"Generate one {difficulty} technical interview question for a {role} about {skill}. One sentence only.",
            }],
            temperature=0.7,
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None
