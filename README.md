
# AI-Mock-interview

# InterviewAI — ATS Resume Analyzer + AI Mock Interview

A Django full-stack platform with **ATS resume analysis** and a **structured ~25-minute voice mock interview** (Web Speech API).

## Features

- **ATS Analyzer**: Upload PDF/DOCX, paste job description, weighted ATS score (keywords + skills), suggestions
- **Mock Interview**: 11 roles, 4-phase flow (intro → technical → behavioral → closing), voice in/out
- **REST API**: Interview session lifecycle via Django REST Framework
- **Reports**: Scores, strengths, weaknesses, PDF download, interview history in admin

## Tech Stack

- Django, Django REST Framework
- PyPDF2, python-docx, NLTK
- Tailwind CSS (CDN), vanilla JavaScript
- Web Speech API (SpeechRecognition + SpeechSynthesis)
- Optional: OpenAI API for smarter evaluation

## Setup

### 1. Prerequisites

- Python 3.10+
- Chrome or Edge (recommended for speech recognition)

### 2. Virtual environment

```bash
cd AI_Interview_Project
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 3. Environment variables

Copy `.env.example` to `.env` in the project root:

```bash
copy .env.example .env
```

Optional (improves answer scoring):

```
OPENAI_API_KEY=sk-...
```

### 4. Database & run

```bash
cd ai_interview
python manage.py migrate
python manage.py runserver
```

Open **http://127.0.0.1:8000/**

## Usage

1. **Home** → **ATS Analyzer** → upload resume + paste JD → view score and skills
2. **Start Mock Interview** → choose role → **Start Interview**
3. Use **mic** for speech-to-text, **Speak** for AI voice, or type answers
4. After ~12 questions or when time ends, view the **report** and download PDF

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interview/start/` | Start session `{ "role", "resume_skills", "job_description" }` |
| GET | `/api/interview/session/<uuid>/` | Session state + current question |
| POST | `/api/interview/answer/` | Submit `{ "session_id", "answer" }` |
| POST | `/api/interview/complete/<uuid>/` | Final report |
| GET | `/api/interview/history/` | Recent completed interviews |

## Project Structure

```
ai_interview/
├── users/
│   ├── services/
│   │   ├── ats_analyzer.py      # ATS scoring
│   │   ├── interview_engine.py  # Questions & evaluation
│   │   ├── text_utils.py        # PDF/DOCX extraction
│   │   └── skills_data.py       # Skills & question banks
│   ├── api_views.py             # REST API
│   └── views.py                 # Page views
├── templates/                   # SaaS UI pages
├── static/js/interview.js       # Voice + chat UI
└── manage.py
```

## Notes

- Mic requires HTTPS or `localhost` and browser permission
- Without OpenAI key, scoring uses keyword + length heuristics (still functional)
- NLTK data downloads automatically on first ATS run
