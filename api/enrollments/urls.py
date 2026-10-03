from django.urls import path

from . import views

urlpatterns = [
    path("learn/<slug:slug>/", views.LessonOutlineView.as_view(), name="learn-outline"),
    path(
        "learn/<slug:slug>/lessons/<uuid:pk>/",
        views.LessonViewerView.as_view(),
        name="learn-lesson",
    ),
    path(
        "users/me/enrollments/",
        views.MyEnrollmentListView.as_view(),
        name="user-me-enrollments",
    ),
    path(
        "admin/users/<uuid:pk>/enrollments/",
        views.AdminUserEnrollmentListView.as_view(),
        name="admin-user-enrollments",
    ),
    path(
        "admin/enrollments/<uuid:pk>/revoke/",
        views.AdminEnrollmentRevokeView.as_view(),
        name="admin-enrollment-revoke",
    ),
    path(
        "admin/enrollments/<uuid:pk>/restore/",
        views.AdminEnrollmentRestoreView.as_view(),
        name="admin-enrollment-restore",
    ),
]
