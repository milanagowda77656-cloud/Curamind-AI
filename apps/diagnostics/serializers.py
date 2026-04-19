"""CuraMind AI - Diagnostics Serializers"""

from rest_framework import serializers
from .models import DiagnosticResult, DiagnosticQueue


class DiagnosticResultSerializer(serializers.ModelSerializer):
    image_filename = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    is_high_risk = serializers.ReadOnlyField()

    class Meta:
        model = DiagnosticResult
        fields = [
            'id', 'image', 'image_filename', 'patient_name',
            'status', 'model_name', 'model_version',
            'anomaly_score', 'confidence', 'findings', 'recommendations',
            'heatmap_file', 'is_high_risk', 'processing_time_ms',
            'reviewed_by', 'reviewed_at', 'radiologist_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = (
            'id', 'status', 'model_name', 'model_version',
            'anomaly_score', 'confidence', 'findings', 'recommendations',
            'heatmap_file', 'processing_time_ms', 'created_at', 'updated_at',
        )

    def get_image_filename(self, obj):
        return obj.image.original_filename

    def get_patient_name(self, obj):
        return obj.image.record.patient.get_full_name()


class DiagnosticReviewSerializer(serializers.ModelSerializer):
    """Used by radiologists/doctors to add review notes."""

    class Meta:
        model = DiagnosticResult
        fields = ['radiologist_notes']


class DiagnosticQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticQueue
        fields = ['id', 'image', 'celery_task_id', 'queued_at', 'started_at', 'completed_at', 'retries']
