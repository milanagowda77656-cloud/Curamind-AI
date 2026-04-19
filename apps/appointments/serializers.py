"""CuraMind AI - Appointments Serializers"""

from rest_framework import serializers
from django.utils import timezone
from .models import Appointment, AppointmentSlot, AppointmentStatus


class AppointmentSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentSlot
        fields = ['id', 'date', 'start_time', 'end_time', 'is_booked']
        read_only_fields = ('is_booked',)


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    is_upcoming = serializers.ReadOnlyField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'patient_name', 'doctor_name',
            'appointment_type', 'status', 'scheduled_at', 'duration_minutes',
            'reason', 'notes', 'cancellation_reason', 'is_upcoming',
            'created_at', 'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'patient')

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_doctor_name(self, obj):
        return f'Dr. {obj.doctor.get_full_name()}'

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Appointment must be scheduled in the future.')
        return value

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """Limited update serializer - only doctors can add notes."""

    class Meta:
        model = Appointment
        fields = ['status', 'notes', 'cancellation_reason']

    def validate_status(self, value):
        instance = self.instance
        user = self.context['request'].user

        # Patients can only cancel
        if user.role == 'PATIENT' and value not in [AppointmentStatus.CANCELLED]:
            raise serializers.ValidationError('Patients can only cancel appointments.')

        return value
