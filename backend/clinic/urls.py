"""URL routing for clinic API endpoints."""

from django.urls import path

from backend.clinic import views

urlpatterns = [
    path("health/", views.health_check, name="api-health"),
    path("patients/", views.patients_collection, name="api-patients"),
    path(
        "patients/<int:patient_id>/appointments/",
        views.patient_appointments,
        name="api-patient-appointments",
    ),
    path("appointments/", views.appointments_collection, name="api-appointments"),
    path(
        "appointments/<int:appointment_id>/status/",
        views.appointment_status,
        name="api-appointment-status",
    ),
]
