"""
CuraMind AI - Diagnostics Models
Stores AI diagnostic analysis results linked to medical images.
"""

import uuid
from django.db import models


class DiagnosticStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review Required'


class DiagnosticResult(models.Model):
    """
    AI Diagnostic result for a MedicalImage.
    Created and populated by the Celery worker after image upload.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.OneToOneField(
        'medical_records.MedicalImage',
        on_delete=models.CASCADE,
        related_name='diagnostic_result'
    )
    status = models.CharField(
        max_length=20,
        choices=DiagnosticStatus.choices,
        default=DiagnosticStatus.QUEUED
    )

    # AI Model outputs
    model_name = models.CharField(max_length=100, default='ResNet50-CuraMind-v1')
    model_version = models.CharField(max_length=20, default='1.0.0')
    anomaly_score = models.FloatField(null=True, blank=True)  # 0.0 – 1.0
    confidence = models.FloatField(null=True, blank=True)     # 0.0 – 1.0
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    heatmap_file = models.FileField(upload_to='heatmaps/', null=True, blank=True)

    # Processing metadata
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Radiologist/Doctor review
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_diagnostics'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    radiologist_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'DiagResult [{self.status}] | Score: {self.anomaly_score} | {self.image.original_filename}'

    @property
    def is_high_risk(self):
        return self.anomaly_score is not None and self.anomaly_score >= 0.7


class DiagnosticQueue(models.Model):
    """Tracks the Celery task queue status for image processing jobs."""

    image = models.OneToOneField(
        'medical_records.MedicalImage',
        on_delete=models.CASCADE,
        related_name='queue_entry'
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retries = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    def __str__(self):
        return f'Queue [{self.celery_task_id}] → {self.image.original_filename}'
