from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from users.models import InterviewAnswer, InterviewSession
from users.serializers import (
    InterviewAnswerSerializer,
    InterviewSessionSerializer,
    InterviewStartSerializer,
)
from users.services.interview_engine import (
    compute_final_report,
    evaluate_answer,
    generate_questions,
    session_time_remaining,
)


@api_view(["POST"])
def interview_start(request):
    ser = InterviewStartSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    questions = generate_questions(
        data["role"],
        resume_skills=data.get("resume_skills") or [],
        job_description=data.get("job_description", ""),
    )

    session = InterviewSession.objects.create(
        role=data["role"],
        questions=questions,
        resume_skills=data.get("resume_skills") or [],
        job_description=data.get("job_description", ""),
    )

    return Response({
        "session": InterviewSessionSerializer(session).data,
        "first_question": questions[0] if questions else None,
        "message": "Interview started. Phase 1: Introduction.",
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def interview_session_detail(request, session_id):
    try:
        session = InterviewSession.objects.get(pk=session_id)
    except InterviewSession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status == "active" and session_time_remaining(session.started_at, session.duration_minutes) <= 0:
        session.status = "expired"
        session.save(update_fields=["status"])

    return Response(InterviewSessionSerializer(session).data)


@api_view(["POST"])
def interview_submit_answer(request):
    ser = InterviewAnswerSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    session_id = ser.validated_data["session_id"]
    answer_text = ser.validated_data["answer"]

    try:
        session = InterviewSession.objects.get(pk=session_id)
    except InterviewSession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    if session.status != "active":
        return Response({"error": "Interview is no longer active."}, status=status.HTTP_400_BAD_REQUEST)

    if session_time_remaining(session.started_at, session.duration_minutes) <= 0:
        session.status = "expired"
        session.save(update_fields=["status"])
        return Response({"error": "Interview time has expired."}, status=status.HTTP_400_BAD_REQUEST)

    idx = session.current_question_index
    if idx >= len(session.questions):
        return Response({"error": "All questions answered."}, status=status.HTTP_400_BAD_REQUEST)

    question = session.questions[idx]
    evaluation = evaluate_answer(
        answer_text,
        question.get("expected_keywords", []),
        question.get("text", ""),
    )

    InterviewAnswer.objects.update_or_create(
        session=session,
        question_index=idx,
        defaults={
            "question_text": question["text"],
            "phase": question.get("phase", ""),
            "difficulty": question.get("difficulty", ""),
            "answer_text": answer_text,
            "score": evaluation["score"],
            "feedback": evaluation.get("feedback", ""),
            "keywords_found": evaluation.get("keywords_found", []),
        },
    )

    session.current_question_index = idx + 1
    session.save(update_fields=["current_question_index"])

    next_question = None
    is_complete = session.current_question_index >= len(session.questions)
    phase_label = question.get("phase", "")

    if not is_complete:
        next_q = session.questions[session.current_question_index]
        next_question = next_q
        phase_label = next_q.get("phase", phase_label)

    return Response({
        "evaluation": evaluation,
        "next_question": next_question,
        "is_complete": is_complete,
        "current_index": session.current_question_index,
        "total": len(session.questions),
        "phase": phase_label,
        "session": InterviewSessionSerializer(session).data,
    })


@api_view(["POST"])
def interview_complete(request, session_id):
    try:
        session = InterviewSession.objects.get(pk=session_id)
    except InterviewSession.DoesNotExist:
        return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    answers_data = []
    for ans in session.answers.all():
        answers_data.append({
            "score": ans.score,
            "phase": ans.phase,
            "question": ans.question_text,
            "feedback": ans.feedback,
        })

    report = compute_final_report(answers_data)
    session.status = "completed"
    session.completed_at = timezone.now()
    session.overall_score = report["overall_score"]
    session.technical_score = report["technical_score"]
    session.communication_score = report["communication_score"]
    session.report = report
    session.save()

    return Response({
        "session": InterviewSessionSerializer(session).data,
        "report": report,
        "answers": [
            {
                "question": a.question_text,
                "answer": a.answer_text,
                "score": a.score,
                "feedback": a.feedback,
                "phase": a.phase,
            }
            for a in session.answers.all()
        ],
    })


@api_view(["GET"])
def interview_history(request):
    sessions = InterviewSession.objects.filter(status="completed")[:20]
    return Response([
        {
            "id": str(s.id),
            "role": s.role,
            "completed_at": s.completed_at,
            "overall_score": s.overall_score,
        }
        for s in sessions
    ])
