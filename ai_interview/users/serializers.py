from rest_framework import serializers

from users.models import InterviewAnswer, InterviewSession
from users.services.skills_data import INTERVIEW_ROLES


class InterviewStartSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=INTERVIEW_ROLES)
    resume_skills = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    job_description = serializers.CharField(required=False, allow_blank=True, default="")


class InterviewAnswerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    answer = serializers.CharField(allow_blank=True)


class InterviewSessionSerializer(serializers.ModelSerializer):
    time_remaining_seconds = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    current_question = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSession
        fields = [
            "id", "role", "status", "started_at", "completed_at",
            "current_question_index", "duration_minutes",
            "overall_score", "technical_score", "communication_score",
            "report", "time_remaining_seconds", "progress_percent",
            "current_question", "total_questions",
        ]

    def get_time_remaining_seconds(self, obj):
        from users.services.interview_engine import session_time_remaining
        if obj.status != "active":
            return 0
        return session_time_remaining(obj.started_at, obj.duration_minutes)

    def get_progress_percent(self, obj):
        from users.services.interview_engine import progress_percent
        total = len(obj.questions)
        return progress_percent(obj.current_question_index, total)

    def get_current_question(self, obj):
        idx = obj.current_question_index
        if idx < len(obj.questions):
            return obj.questions[idx]
        return None

    def get_total_questions(self, obj):
        return len(obj.questions)


class InterviewAnswerRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewAnswer
        fields = [
            "question_index", "question_text", "phase", "difficulty",
            "answer_text", "score", "feedback", "keywords_found", "answered_at",
        ]
