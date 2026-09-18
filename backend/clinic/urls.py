"""URL routing for clinic API endpoints."""

from django.urls import path

from backend.clinic import views

urlpatterns = [
    path("health/", views.health_check, name="api-health"),
    path("patients/", views.patients_collection, name="api-patients"),
    path("patients/<int:patient_id>/", views.patient_detail, name="api-patient-detail"),
    path(
        "patients/<int:patient_id>/appointments/",
        views.patient_appointments,
        name="api-patient-appointments",
    ),
    path("appointments/", views.appointments_collection, name="api-appointments"),
    path(
        "appointments/<int:appointment_id>/",
        views.appointment_detail,
        name="api-appointment-detail",
    ),
    path(
        "appointments/<int:appointment_id>/status/",
        views.appointment_status,
        name="api-appointment-status",
    ),
    # Authentication & Staff
    path("auth/register/", views.auth_register, name="api-auth-register"),
    path("auth/login/", views.auth_login, name="api-auth-login"),
    path("auth/me/", views.auth_me, name="api-auth-me"),
    path("auth/logout/", views.auth_logout, name="api-auth-logout"),
    path("auth/profile/", views.auth_profile, name="api-auth-profile"),
    path("doctors/", views.doctors_collection, name="api-doctors"),
]
