from django.contrib import admin

from .models import ATSAnalysis, InterviewAnswer, InterviewSession


@admin.register(ATSAnalysis)
class ATSAnalysisAdmin(admin.ModelAdmin):
    list_display = ("ats_score", "resume_filename", "created_at")
    list_filter = ("created_at",)
    search_fields = ("resume_filename",)


class InterviewAnswerInline(admin.TabularInline):
    model = InterviewAnswer
    extra = 0
    readonly_fields = ("question_text", "answer_text", "score", "phase")


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ("role", "status", "overall_score", "started_at", "completed_at")
    list_filter = ("role", "status")
    inlines = [InterviewAnswerInline]
