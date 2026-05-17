from django.urls import path

from . import api_views, views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("interview/setup/", views.interview_setup, name="interview_setup"),
    path("interview/", views.interview_room, name="interview_room"),
    path("interview/report/<uuid:session_id>/", views.interview_report, name="interview_report"),
    path(
        "interview/report/<uuid:session_id>/pdf/",
        views.download_report_pdf,
        name="interview_report_pdf",
    ),
    # REST API
    path("api/interview/start/", api_views.interview_start, name="api_interview_start"),
    path("api/interview/session/<uuid:session_id>/", api_views.interview_session_detail, name="api_interview_session"),
    path("api/interview/answer/", api_views.interview_submit_answer, name="api_interview_answer"),
    path("api/interview/complete/<uuid:session_id>/", api_views.interview_complete, name="api_interview_complete"),
    path("api/interview/history/", api_views.interview_history, name="api_interview_history"),
]
