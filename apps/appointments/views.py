"""CuraMind AI - Appointments Views"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.audit.utils import log_action
from .models import Appointment, AppointmentSlot
from .serializers import AppointmentSerializer, AppointmentUpdateSerializer, AppointmentSlotSerializer


class AppointmentListCreateView(generics.ListCreateAPIView):
    """List appointments for current user; patients book new ones."""
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'appointment_type']
    search_fields = ['reason']
    ordering_fields = ['scheduled_at', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.PATIENT:
            return Appointment.objects.filter(patient=user).select_related('doctor', 'patient')
        elif user.role == UserRole.DOCTOR:
            return Appointment.objects.filter(doctor=user).select_related('doctor', 'patient')
        elif user.role in [UserRole.NURSE, UserRole.ADMIN]:
            return Appointment.objects.all().select_related('doctor', 'patient')
        return Appointment.objects.none()

    def perform_create(self, serializer):
        appt = serializer.save()
        log_action(self.request.user, 'CREATE_APPOINTMENT', 'Appointment', str(appt.id), request=self.request)


class AppointmentDetailView(generics.RetrieveUpdateAPIView):
    """Get or update a specific appointment."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.PATIENT:
            return Appointment.objects.filter(patient=user)
        elif user.role == UserRole.DOCTOR:
            return Appointment.objects.filter(doctor=user)
        return Appointment.objects.all()

    def perform_update(self, serializer):
        appt = serializer.save()
        log_action(self.request.user, 'UPDATE_APPOINTMENT', 'Appointment', str(appt.id), request=self.request)


class DoctorAvailabilityView(generics.ListAPIView):
    """List available slots for a given doctor."""
    serializer_class = AppointmentSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        doctor_id = self.kwargs['doctor_id']
        return AppointmentSlot.objects.filter(
            doctor_id=doctor_id,
            is_booked=False,
            date__gte=timezone.now().date()
        ).order_by('date', 'start_time')


class UpcomingAppointmentsView(generics.ListAPIView):
    """Quick view of upcoming appointments for the authenticated user."""
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.filter(
            scheduled_at__gt=timezone.now(),
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('doctor', 'patient')
        if user.role == UserRole.PATIENT:
            return qs.filter(patient=user)
        elif user.role == UserRole.DOCTOR:
            return qs.filter(doctor=user)
        return qs
