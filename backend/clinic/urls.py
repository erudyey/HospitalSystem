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
    path("appointments/walk-in/", views.appointment_walk_in, name="api-appointment-walk-in"),
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
    path("auth/status/", views.auth_status, name="api-auth-status"),
    path("auth/login/", views.auth_login, name="api-auth-login"),
    path("demo/accounts/", views.demo_accounts, name="api-demo-accounts"),
    path("demo/login/", views.demo_login, name="api-demo-login"),
    path("auth/me/", views.auth_me, name="api-auth-me"),
    path("auth/logout/", views.auth_logout, name="api-auth-logout"),
    path("auth/profile/", views.auth_profile, name="api-auth-profile"),
    path("doctors/", views.doctors_collection, name="api-doctors"),
    # Clinical Views, Conflict Engine, and Medical Records
    path(
        "appointments/conflict-check/",
        views.check_conflict,
        name="api-appointment-conflict-check",
    ),
    path("doctor/queue/", views.doctor_queue, name="api-doctor-queue"),
    path("doctor/patients/", views.doctor_patients, name="api-doctor-patients"),
    path(
        "doctor/appointments/",
        views.doctor_appointments,
        name="api-doctor-appointments",
    ),
    path(
        "patients/<int:patient_id>/medical-records/",
        views.patient_medical_records,
        name="api-patient-medical-records",
    ),
    path(
        "medical-records/",
        views.medical_records_collection,
        name="api-medical-records",
    ),
    path(
        "medical-records/<int:record_id>/",
        views.medical_record_detail,
        name="api-medical-record-detail",
    ),
]
