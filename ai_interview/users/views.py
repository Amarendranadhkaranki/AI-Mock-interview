import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from users.models import ATSAnalysis, InterviewSession
from users.services.ats_analyzer import analyze_resume
from users.services.skills_data import INTERVIEW_ROLES
def home(request):
    recent_ats = ATSAnalysis.objects.all()[:3]
    recent_interviews = InterviewSession.objects.filter(status="completed")[:3]
    return render(request, "users/index.html", {
        "recent_ats": recent_ats,
        "recent_interviews": recent_interviews,
    })


@require_http_methods(["GET", "POST"])
def upload(request):
    if request.method == "POST":
        resume = request.FILES.get("resume")
        jd = request.POST.get("jd", "")

        if not resume:
            return render(request, "users/upload.html", {"error": "Please upload a resume file."})
        if not jd.strip():
            return render(request, "users/upload.html", {"error": "Please paste the job description."})

        name_lower = resume.name.lower()
        if not (name_lower.endswith(".pdf") or name_lower.endswith(".docx")):
            return render(request, "users/upload.html", {
                "error": "Unsupported format. Please upload PDF or DOCX only.",
            })

        try:
            result = analyze_resume(resume, jd)
        except ValueError as e:
            return render(request, "users/upload.html", {"error": str(e)})
        except Exception:
            return render(request, "users/upload.html", {
                "error": "Failed to process resume. Please try another file.",
            })

        analysis = ATSAnalysis.objects.create(
            resume_filename=resume.name,
            job_description=jd,
            ats_score=result["ats_score"],
            keyword_score=result["keyword_score"],
            skill_score=result["skill_score"],
            matched_keywords=result["matched_keywords"],
            missing_keywords=result["missing_keywords"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            resume_skills=result["resume_skills"],
            suggestions=result["suggestions"],
        )

        request.session["last_ats_id"] = analysis.id
        request.session["resume_skills"] = result["resume_skills"]
        request.session["job_description"] = jd

        return render(request, "users/result.html", {
            "analysis": analysis,
            "score": result["ats_score"],
            "keyword_score": result["keyword_score"],
            "skill_score": result["skill_score"],
            "matched": result["matched_keywords"],
            "missing": result["missing_keywords"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "resume_skills": result["resume_skills"],
            "suggestions": result["suggestions"],
            "text_preview": result["resume_text_preview"],
        })

    return render(request, "users/upload.html")


def interview_setup(request):
    resume_skills = request.session.get("resume_skills", [])
    job_description = request.session.get("job_description", "")
    return render(request, "users/interview_setup.html", {
        "roles": INTERVIEW_ROLES,
        "resume_skills": resume_skills,
        "resume_skills_json": json.dumps(resume_skills),
        "job_description": job_description,
    })


def interview_room(request):
    return render(request, "users/interview.html")


def interview_report(request, session_id):
    session = get_object_or_404(InterviewSession, pk=session_id)
    return render(request, "users/interview_report.html", {
        "session": session,
        "report": session.report or {},
        "answers": session.answers.all(),
    })


def download_report_pdf(request, session_id):
    session = get_object_or_404(InterviewSession, pk=session_id)
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        y = 750
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, f"Interview Report — {session.role}")
        y -= 30
        p.setFont("Helvetica", 11)
        report = session.report or {}
        scores = {
            "Overall Score": session.overall_score or report.get("overall_score", "N/A"),
            "Technical Score": session.technical_score or report.get("technical_score", "N/A"),
            "Communication Score": session.communication_score or report.get("communication_score", "N/A"),
        }
        for label, val in scores.items():
            p.drawString(50, y, f"{label}: {val}")
            y -= 18
        y -= 10
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Strengths")
        y -= 18
        p.setFont("Helvetica", 10)
        for s in report.get("strengths", []):
            p.drawString(60, y, f"• {s[:90]}")
            y -= 14
        y -= 8
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Suggestions")
        y -= 18
        p.setFont("Helvetica", 10)
        for s in report.get("suggestions", []):
            p.drawString(60, y, f"• {s[:90]}")
            y -= 14
        p.showPage()
        p.save()
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="interview_report_{session_id}.pdf"'
        return response
    except Exception:
        return redirect("interview_report", session_id=session_id)
