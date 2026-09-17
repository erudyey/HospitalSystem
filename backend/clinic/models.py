"""Database models for patients and appointments."""

from django.core.exceptions import ValidationError
from django.db import models


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "Scheduled", "Scheduled"
    COMPLETED = "Completed", "Completed"
    CANCELLED = "Cancelled", "Cancelled"


class Patient(models.Model):
    """Patient record uniquely identified by an integer ID."""

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
    """Appointment record associating a patient with a doctor and date."""

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
        db_index=True,
    )
    doctor_name = models.CharField(max_length=150)
    app_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
    )

    class Meta:
        db_table = "clinic_appointments"
        ordering = ["id"]

    def clean(self) -> None:
        if self.doctor_name is not None:
            self.doctor_name = self.doctor_name.strip()
        if not self.doctor_name:
            raise ValidationError({"doctor_name": "Doctor name is required."})

        if self.status not in AppointmentStatus.values:
            raise ValidationError({"status": f"Invalid status '{self.status}'."})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Appointment #{self.id} for {self.patient.full_name} with {self.doctor_name}"
