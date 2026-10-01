from django.urls import path

from . import views

urlpatterns = [
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
