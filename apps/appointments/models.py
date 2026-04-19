"""CuraMind AI - Appointments Models"""

import uuid
from django.db import models
from django.utils import timezone


class AppointmentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    COMPLETED = 'COMPLETED', 'Completed'
    NO_SHOW = 'NO_SHOW', 'No Show'


class AppointmentType(models.TextChoices):
    GENERAL = 'GENERAL', 'General Consultation'
    FOLLOWUP = 'FOLLOWUP', 'Follow-up'
    DIAGNOSTIC = 'DIAGNOSTIC', 'Diagnostic Review'
    IMAGING = 'IMAGING', 'Imaging Review'
    EMERGENCY = 'EMERGENCY', 'Emergency'


class Appointment(models.Model):
    """
    Appointment model linking a patient to a doctor.
    Includes scheduling, status tracking, and notes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'role': 'PATIENT'}
    )
    doctor = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'role': 'DOCTOR'}
    )
    appointment_type = models.CharField(
        max_length=20, choices=AppointmentType.choices,
        default=AppointmentType.GENERAL
    )
    status = models.CharField(
        max_length=20, choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.TextField()
    notes = models.TextField(blank=True)  # Doctor's notes post-appointment
    cancellation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'scheduled_at']),
        ]

    def __str__(self):
        return f'{self.patient.get_full_name()} → Dr. {self.doctor.get_full_name()} @ {self.scheduled_at}'

    @property
    def is_upcoming(self):
        return self.scheduled_at > timezone.now() and self.status in [
            AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED
        ]


class AppointmentSlot(models.Model):
    """
    Available time slots for a doctor.
    Allows the system to check availability before booking.
    """

    doctor = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='appointment_slots',
        limit_choices_to={'role': 'DOCTOR'}
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='slot'
    )

    class Meta:
        unique_together = ('doctor', 'date', 'start_time')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'Dr. {self.doctor.get_full_name()} | {self.date} {self.start_time}-{self.end_time}'
