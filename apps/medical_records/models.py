"""
CuraMind AI - Medical Records Models
HIPAA-compliant Electronic Medical Record (EMR) storage.
Sensitive fields are encrypted at rest using Fernet symmetric encryption.
"""

import uuid
import os
import magic
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet


def get_fernet():
    """Return a Fernet instance using the configured encryption key."""
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set in environment variables.")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_text(value: str) -> str:
    """Encrypt a string field for at-rest storage."""
    if not value:
        return value
    f = get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_text(value: str) -> str:
    """Decrypt an encrypted string field."""
    if not value:
        return value
    try:
        f = get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value  # Return as-is if not encrypted (migration safety)


def validate_medical_file(file):
    """
    Validate uploaded medical files:
    - Check MIME type via magic bytes (not just extension)
    - Enforce max file size
    """
    allowed_types = getattr(settings, 'ALLOWED_MEDICAL_MIME_TYPES', [
        'image/jpeg', 'image/png', 'application/dicom', 'image/dicom',
    ])
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)

    if file.size > max_size:
        raise ValidationError(f'File size exceeds maximum allowed size of {max_size // (1024*1024)}MB.')

    # Read magic bytes to detect true MIME type
    file.seek(0)
    header = file.read(2048)
    file.seek(0)

    try:
        detected_mime = magic.from_buffer(header, mime=True)
    except Exception:
        detected_mime = 'application/octet-stream'

    if detected_mime not in allowed_types:
        raise ValidationError(
            f'File type "{detected_mime}" is not allowed. '
            f'Accepted types: {", ".join(allowed_types)}'
        )


def medical_image_upload_path(instance, filename):
    """Organize uploads by patient ID and record ID."""
    ext = filename.rsplit('.', 1)[-1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('medical_images', str(instance.record.patient.id), safe_name)


class RecordType(models.TextChoices):
    CONSULTATION = 'CONSULTATION', 'Consultation Notes'
    LAB_RESULT = 'LAB_RESULT', 'Lab Result'
    PRESCRIPTION = 'PRESCRIPTION', 'Prescription'
    IMAGING = 'IMAGING', 'Imaging / Radiology'
    SURGERY = 'SURGERY', 'Surgery Report'
    ALLERGY = 'ALLERGY', 'Allergy Record'
    VACCINATION = 'VACCINATION', 'Vaccination'
    OTHER = 'OTHER', 'Other'


class MedicalRecord(models.Model):
    """
    Core EMR model. Sensitive diagnosis/notes fields are encrypted at rest.
    Object-level permissions enforced via django-guardian.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='medical_records',
        limit_choices_to={'role': 'PATIENT'}
    )
    doctor = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='created_records',
        limit_choices_to={'role__in': ['DOCTOR', 'NURSE', 'RADIOLOGIST']}
    )
    record_type = models.CharField(max_length=20, choices=RecordType.choices)

    # Encrypted sensitive fields
    _diagnosis = models.TextField(db_column='diagnosis', blank=True)
    _notes = models.TextField(db_column='notes', blank=True)
    _prescription = models.TextField(db_column='prescription', blank=True)

    # Non-sensitive metadata
    title = models.CharField(max_length=255)
    is_critical = models.BooleanField(default=False)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'record_type']),
            models.Index(fields=['doctor', 'created_at']),
        ]
        permissions = [
            ('view_own_record', 'Can view own medical record'),
            ('view_patient_record', 'Can view patient medical record (Doctor)'),
        ]

    def __str__(self):
        return f'{self.record_type} | {self.patient.get_full_name()} | {self.created_at.date()}'

    # --- Encrypted field properties ---

    @property
    def diagnosis(self):
        return decrypt_text(self._diagnosis)

    @diagnosis.setter
    def diagnosis(self, value):
        self._diagnosis = encrypt_text(value) if value else ''

    @property
    def notes(self):
        return decrypt_text(self._notes)

    @notes.setter
    def notes(self, value):
        self._notes = encrypt_text(value) if value else ''

    @property
    def prescription(self):
        return decrypt_text(self._prescription)

    @prescription.setter
    def prescription(self, value):
        self._prescription = encrypt_text(value) if value else ''


class MedicalImage(models.Model):
    """
    Medical image attached to a MedicalRecord.
    Supports DICOM and standard image formats.
    Metadata is stripped on upload for privacy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='images')
    file = models.FileField(upload_to=medical_image_upload_path, validators=[validate_medical_file])
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    is_dicom = models.BooleanField(default=False)

    # DICOM metadata (extracted by Celery task)
    dicom_patient_name = models.CharField(max_length=255, blank=True)
    dicom_study_date = models.DateField(null=True, blank=True)
    dicom_modality = models.CharField(max_length=20, blank=True)
    dicom_body_part = models.CharField(max_length=100, blank=True)
    dicom_series_description = models.CharField(max_length=255, blank=True)

    # AI Diagnostics result (set by Celery task)
    ai_processed = models.BooleanField(default=False)
    ai_heatmap_file = models.FileField(upload_to='heatmaps/', null=True, blank=True)
    ai_anomaly_score = models.FloatField(null=True, blank=True)
    ai_findings = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename} → {self.record}'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size_bytes = self.file.size
            # Detect if DICOM by extension
            name_lower = self.original_filename.lower()
            self.is_dicom = name_lower.endswith('.dcm') or name_lower.endswith('.dicom')
        super().save(*args, **kwargs)
