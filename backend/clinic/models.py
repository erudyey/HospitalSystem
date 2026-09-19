"""Database models for staff, patients, appointments, and clinical records."""

import re

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "Scheduled", "Scheduled"
    CHECKED_IN = "Checked In", "Checked In"
    IN_CONSULTATION = "In Consultation", "In Consultation"
    COMPLETED = "Completed", "Completed"
    CANCELLED = "Cancelled", "Cancelled"


class StaffRole(models.TextChoices):
    RECEPTIONIST = "receptionist", "Receptionist"
    DOCTOR = "doctor", "Doctor"


class StaffUser(models.Model):
    """Staff member account with role-based access control and hashed credentials."""

    id: int
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=StaffRole.choices,
        default=StaffRole.RECEPTIONIST,
    )
    specialty = models.CharField(max_length=100, blank=True, default="")
    license_number = models.CharField(max_length=50, blank=True, default="")
    contact = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clinic_staff_users"
        ordering = ["full_name", "id"]

    def set_password(self, raw_password: str) -> None:
        """Hash and assign the staff member password using PBKDF2-SHA256."""
        if not raw_password or len(raw_password) < 6:
            raise ValidationError({"password": "Password must be at least 6 characters long."})
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify password against the stored cryptographic hash."""
        return check_password(raw_password, self.password_hash)

    def clean(self) -> None:
        if self.username is not None:
            self.username = self.username.strip().lower()
        if not self.username:
            raise ValidationError({"username": "Username is required."})
        if not re.match(r"^[a-z0-9_.-]+$", self.username):
            raise ValidationError(
                {
                    "username": "Username may only contain letters, numbers, hyphens, dots, and underscores."
                }
            )

        if self.full_name is not None:
            self.full_name = self.full_name.strip()
        if not self.full_name:
            raise ValidationError({"full_name": "Full name is required."})

        if self.role not in StaffRole.values:
            raise ValidationError({"role": f"Invalid role '{self.role}'."})

        if self.contact is not None:
            self.contact = self.contact.strip()
        if self.specialty is not None:
            self.specialty = self.specialty.strip()
        if self.license_number is not None:
            self.license_number = self.license_number.strip()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        specialty_str = f" ({self.specialty})" if self.specialty else ""
        role_label = StaffRole(self.role).label if self.role in StaffRole.values else self.role
        return f"{self.full_name} [{role_label}]{specialty_str}"


class UserSession(models.Model):
    """Authenticated staff session on the local workstation."""

    token = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        StaffUser,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinic_user_sessions"
        ordering = ["-last_active"]

    def __str__(self) -> str:
        return f"Session for {self.user.username} (active {self.last_active})"


class Patient(models.Model):
    """Patient record uniquely identified by an integer ID."""

    id: int
    full_name = models.CharField(max_length=150)
    contact = models.CharField(max_length=100, blank=True, default="")
    age = models.PositiveIntegerField()

    class Meta:
        db_table = "clinic_patients"
        ordering = ["id"]

    def clean(self) -> None:
        if self.full_name is not None:
            self.full_name = self.full_name.strip()
        if not self.full_name:
            raise ValidationError({"full_name": "Full name is required."})

        if self.contact is not None:
            self.contact = self.contact.strip()

        if self.age is None or self.age <= 0:
            raise ValidationError({"age": "Age must be a positive whole number greater than 0."})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} (ID: {self.id})"


class Appointment(models.Model):
    """Appointment record associating a patient with a doctor, date, and time slot."""

    id: int
    patient_id: int
    doctor_id: int | None
    conflict_overridden_by_id: int | None
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
        db_index=True,
    )
    doctor = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctor_appointments",
    )
    doctor_name = models.CharField(max_length=150)
    app_date = models.DateField()
    app_time = models.TimeField(default="09:00:00")
    reason_for_visit = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    conflict_override_reason = models.CharField(max_length=255, blank=True, default="")
    conflict_overridden_at = models.DateTimeField(null=True, blank=True)
    conflict_overridden_by = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_conflict_overrides",
    )

    class Meta:
        db_table = "clinic_appointments"
        ordering = ["app_date", "app_time", "id"]
        indexes = [
            models.Index(fields=["doctor", "app_date", "status"]),
            models.Index(fields=["app_date", "app_time"]),
        ]

    def clean(self) -> None:
        if self.doctor_name is not None:
            self.doctor_name = self.doctor_name.strip()
        if not self.doctor_name:
            if self.doctor and self.doctor.full_name:
                self.doctor_name = self.doctor.full_name
            else:
                raise ValidationError({"doctor_name": "Doctor name is required."})

        if self.reason_for_visit is not None:
            self.reason_for_visit = self.reason_for_visit.strip()

        if self.status not in AppointmentStatus.values:
            raise ValidationError({"status": f"Invalid status '{self.status}'."})

    def save(self, *args, **kwargs) -> None:
        if self.doctor and not self.doctor_name:
            self.doctor_name = self.doctor.full_name
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"Appointment #{self.id} for {self.patient.full_name} with {self.doctor_name} "
            f"on {self.app_date} at {self.app_time}"
        )


class MedicalRecord(models.Model):
    """Clinical documentation recorded by an attending physician."""

    id: int
    patient_id: int
    doctor_id: int
    appointment_id: int | None
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="medical_records",
    )
    doctor = models.ForeignKey(
        StaffUser,
        on_delete=models.PROTECT,
        related_name="doctor_records",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records",
    )
    diagnosis = models.CharField(max_length=255)
    symptoms = models.TextField(blank=True, default="")
    clinical_notes = models.TextField(blank=True, default="")
    prescription = models.TextField(blank=True, default="")
    follow_up_advice = models.TextField(blank=True, default="")
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinic_medical_records"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["appointment"],
                condition=models.Q(appointment__isnull=False),
                name="unique_appointment_medical_record",
            ),
        ]

    def clean(self) -> None:
        if self.diagnosis is not None:
            self.diagnosis = self.diagnosis.strip()
        if not self.diagnosis:
            raise ValidationError({"diagnosis": "Primary diagnosis is required."})

        if self.symptoms is not None:
            self.symptoms = self.symptoms.strip()
        if self.clinical_notes is not None:
            self.clinical_notes = self.clinical_notes.strip()
        if self.prescription is not None:
            self.prescription = self.prescription.strip()
        if self.follow_up_advice is not None:
            self.follow_up_advice = self.follow_up_advice.strip()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Record #{self.id}: {self.diagnosis} for {self.patient.full_name} by {self.doctor.full_name}"


class MedicalRecordRevision(models.Model):
    """Immutable audit snapshot created whenever an author corrects a medical record."""

    record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision = models.PositiveIntegerField()
    correction_reason = models.CharField(max_length=255)
    diagnosis = models.CharField(max_length=255)
    symptoms = models.TextField(blank=True, default="")
    clinical_notes = models.TextField(blank=True, default="")
    prescription = models.TextField(blank=True, default="")
    follow_up_advice = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(
        StaffUser,
        on_delete=models.PROTECT,
        related_name="medical_record_revisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clinic_medical_record_revisions"
        ordering = ["record_id", "revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["record", "revision"],
                name="unique_medical_record_revision",
            )
        ]
