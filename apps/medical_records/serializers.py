"""CuraMind AI - Medical Records Serializers"""

from rest_framework import serializers
from .models import MedicalRecord, MedicalImage


class MedicalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalImage
        fields = [
            'id', 'file', 'original_filename', 'mime_type', 'file_size_bytes',
            'is_dicom', 'dicom_modality', 'dicom_body_part', 'dicom_study_date',
            'dicom_series_description', 'ai_processed', 'ai_heatmap_file',
            'ai_anomaly_score', 'ai_findings', 'uploaded_at',
        ]
        read_only_fields = (
            'id', 'mime_type', 'file_size_bytes', 'is_dicom',
            'dicom_patient_name', 'dicom_study_date', 'dicom_modality',
            'dicom_body_part', 'dicom_series_description',
            'ai_processed', 'ai_heatmap_file', 'ai_anomaly_score', 'ai_findings',
            'uploaded_at',
        )

    def validate_file(self, value):
        from .models import validate_medical_file
        validate_medical_file(value)
        return value

    def create(self, validated_data):
        validated_data['original_filename'] = validated_data['file'].name

        # Detect MIME type
        try:
            import magic
            validated_data['file'].seek(0)
            header = validated_data['file'].read(2048)
            validated_data['file'].seek(0)
            validated_data['mime_type'] = magic.from_buffer(header, mime=True)
        except Exception:
            validated_data['mime_type'] = 'application/octet-stream'

        instance = super().create(validated_data)

        # Trigger async DICOM processing + AI analysis
        from apps.diagnostics.tasks import process_medical_image
        process_medical_image.delay(str(instance.id))

        return instance


class MedicalRecordSerializer(serializers.ModelSerializer):
    images = MedicalImageSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    # Encrypted fields exposed as plain text to authorized users
    diagnosis = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    prescription = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'doctor', 'patient_name', 'doctor_name',
            'record_type', 'title', 'diagnosis', 'notes', 'prescription',
            'is_critical', 'follow_up_required', 'follow_up_date',
            'images', 'created_at', 'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'doctor')

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_doctor_name(self, obj):
        return f'Dr. {obj.doctor.get_full_name()}'

    def create(self, validated_data):
        # Encrypt sensitive fields on write
        record = MedicalRecord(
            patient=validated_data['patient'],
            doctor=self.context['request'].user,
            record_type=validated_data['record_type'],
            title=validated_data['title'],
            is_critical=validated_data.get('is_critical', False),
            follow_up_required=validated_data.get('follow_up_required', False),
            follow_up_date=validated_data.get('follow_up_date'),
        )
        record.diagnosis = validated_data.get('diagnosis', '')
        record.notes = validated_data.get('notes', '')
        record.prescription = validated_data.get('prescription', '')
        record.save()
        return record

    def update(self, instance, validated_data):
        for field in ['title', 'record_type', 'is_critical', 'follow_up_required', 'follow_up_date']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        if 'diagnosis' in validated_data:
            instance.diagnosis = validated_data['diagnosis']
        if 'notes' in validated_data:
            instance.notes = validated_data['notes']
        if 'prescription' in validated_data:
            instance.prescription = validated_data['prescription']
        instance.save()
        return instance


class MedicalRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — omits encrypted sensitive fields."""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient_name', 'doctor_name', 'record_type', 'title',
            'is_critical', 'follow_up_required', 'created_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_doctor_name(self, obj):
        return f'Dr. {obj.doctor.get_full_name()}'


class MedicalImageUploadSerializer(serializers.ModelSerializer):
    """Used for the image upload endpoint."""

    class Meta:
        model = MedicalImage
        fields = ['id', 'record', 'file', 'original_filename', 'uploaded_at']
        read_only_fields = ('id', 'original_filename', 'uploaded_at')
