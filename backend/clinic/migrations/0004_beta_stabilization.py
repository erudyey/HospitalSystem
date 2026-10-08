"""Add beta clinical audit and scheduling metadata."""

import django.db.models.deletion
from django.db import migrations, models


def snapshot_existing_records(apps, schema_editor):
    MedicalRecord = apps.get_model("clinic", "MedicalRecord")
    MedicalRecordRevision = apps.get_model("clinic", "MedicalRecordRevision")
    for record in MedicalRecord.objects.all().iterator():
        MedicalRecordRevision.objects.get_or_create(
            record_id=record.id,
            revision=1,
            defaults={
                "correction_reason": "Baseline snapshot created during v0.1.0-beta.1 upgrade.",
                "diagnosis": record.diagnosis,
                "symptoms": record.symptoms,
                "clinical_notes": record.clinical_notes,
                "prescription": record.prescription,
                "follow_up_advice": record.follow_up_advice,
                "changed_by_id": record.doctor_id,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("clinic", "0003_staffuser_is_active_alter_medicalrecord_doctor_and_more")]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="checked_in_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="conflict_override_reason",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="appointment",
            name="conflict_overridden_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="conflict_overridden_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="appointment_conflict_overrides",
                to="clinic.staffuser",
            ),
        ),
        migrations.AddField(
            model_name="medicalrecord",
            name="revision",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="MedicalRecordRevision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("revision", models.PositiveIntegerField()),
                ("correction_reason", models.CharField(max_length=255)),
                ("diagnosis", models.CharField(max_length=255)),
                ("symptoms", models.TextField(blank=True, default="")),
                ("clinical_notes", models.TextField(blank=True, default="")),
                ("prescription", models.TextField(blank=True, default="")),
                ("follow_up_advice", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medical_record_revisions",
                        to="clinic.staffuser",
                    ),
                ),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revisions",
                        to="clinic.medicalrecord",
                    ),
                ),
            ],
            options={
                "db_table": "clinic_medical_record_revisions",
                "ordering": ["record_id", "revision"],
            },
        ),
        migrations.AddConstraint(
            model_name="medicalrecordrevision",
            constraint=models.UniqueConstraint(
                fields=("record", "revision"), name="unique_medical_record_revision"
            ),
        ),
        migrations.RunPython(snapshot_existing_records, migrations.RunPython.noop),
    ]
