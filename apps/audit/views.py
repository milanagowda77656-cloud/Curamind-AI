"""CuraMind AI - Audit Views (read-only, admin-accessible)"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsAdminUser, IsDoctor
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    Read-only audit log view.
    Admins see all logs. Doctors see only their own actions.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['action', 'resource_type']
    search_fields = ['user__email', 'resource_id', 'ip_address']
    ordering_fields = ['timestamp']

    def get_queryset(self):
        from apps.accounts.models import UserRole
        user = self.request.user
        if user.role == UserRole.ADMIN or user.is_superuser:
            return AuditLog.objects.select_related('user').all()
        # Doctors/nurses can only view their own audit trail
        return AuditLog.objects.filter(user=user).select_related('user')


class PatientAuditLogView(generics.ListAPIView):
    """Audit logs for a specific patient's records (admin/doctor only)."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        patient_id = self.kwargs['patient_id']
        return AuditLog.objects.filter(
            extra_data__patient_id=str(patient_id)
        ).select_related('user')
