import uuid

from django.db import models

from users.services.skills_data import INTERVIEW_ROLES


class ATSAnalysis(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    resume_filename = models.CharField(max_length=255, blank=True)
    job_description = models.TextField()
    ats_score = models.FloatField(default=0)
    keyword_score = models.FloatField(default=0)
    skill_score = models.FloatField(default=0)
    matched_keywords = models.JSONField(default=list)
    missing_keywords = models.JSONField(default=list)
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    resume_skills = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ATS {self.ats_score}% — {self.created_at:%Y-%m-%d}"


class InterviewSession(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=64, choices=[(r, r) for r in INTERVIEW_ROLES])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_question_index = models.PositiveIntegerField(default=0)
    questions = models.JSONField(default=list)
    resume_skills = models.JSONField(default=list)
    job_description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=25)

    overall_score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    communication_score = models.FloatField(null=True, blank=True)
    report = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.role} — {self.status}"


class InterviewAnswer(models.Model):
    session = models.ForeignKey(
        InterviewSession, on_delete=models.CASCADE, related_name="answers"
    )
    question_index = models.PositiveIntegerField()
    question_text = models.TextField()
    phase = models.CharField(max_length=32)
    difficulty = models.CharField(max_length=16, blank=True)
    answer_text = models.TextField()
    score = models.FloatField(default=0)
    feedback = models.TextField(blank=True)
    keywords_found = models.JSONField(default=list)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_index"]
        unique_together = [["session", "question_index"]]
