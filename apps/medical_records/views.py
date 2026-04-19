"""CuraMind AI - Medical Records Views with HIPAA-compliant RBAC"""

from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.accounts.permissions import IsDoctor, IsDoctorOrNurse, IsOwnerOrDoctor
from apps.audit.utils import log_action
from .models import MedicalRecord, MedicalImage
from .serializers import (
    MedicalRecordSerializer, MedicalRecordListSerializer,
    MedicalImageSerializer, MedicalImageUploadSerializer,
)


class MedicalRecordListCreateView(generics.ListCreateAPIView):
    """
    GET  - List records (scoped by role)
    POST - Create a new record (doctors/nurses only)
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = ['record_type', 'is_critical', 'follow_up_required']
    search_fields = ['title']
    ordering_fields = ['created_at']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return MedicalRecordListSerializer
        return MedicalRecordSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsDoctorOrNurse()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.PATIENT:
            # Patients see ONLY their own records
            return MedicalRecord.objects.filter(patient=user).select_related('patient', 'doctor')
        elif user.role == UserRole.DOCTOR:
            # Doctors see records they created or their patients' records
            return MedicalRecord.objects.filter(
                patient__patient_profile__primary_doctor=user
            ).select_related('patient', 'doctor')
        elif user.role == UserRole.NURSE:
            # Nurses: read-only access to all (enforced by serializer + method check)
            return MedicalRecord.objects.all().select_related('patient', 'doctor')
        elif user.role == UserRole.RADIOLOGIST:
            # Radiologists see imaging records only
            return MedicalRecord.objects.filter(record_type='IMAGING').select_related('patient', 'doctor')
        elif user.role == UserRole.ADMIN:
            # Admins: NO access to private patient medical data (HIPAA)
            return MedicalRecord.objects.none()
        return MedicalRecord.objects.none()

    def perform_create(self, serializer):
        record = serializer.save()
        log_action(
            self.request.user, 'CREATE_RECORD', 'MedicalRecord',
            str(record.id), request=self.request,
            extra={'record_type': record.record_type, 'patient_id': str(record.patient.id)}
        )


class MedicalRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - View full record with decrypted sensitive fields
    PUT    - Update record (doctors only)
    DELETE - Soft delete via is_active flag (doctors only)
    """
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.PATIENT:
            return MedicalRecord.objects.filter(patient=user)
        elif user.role == UserRole.DOCTOR:
            return MedicalRecord.objects.filter(
                patient__patient_profile__primary_doctor=user
            )
        elif user.role == UserRole.RADIOLOGIST:
            return MedicalRecord.objects.filter(record_type='IMAGING')
        elif user.role == UserRole.NURSE:
            return MedicalRecord.objects.all()
        return MedicalRecord.objects.none()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        log_action(
            request.user, 'VIEW_RECORD', 'MedicalRecord',
            str(instance.id), request=request,
            extra={'patient_id': str(instance.patient.id)}
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        record = serializer.save()
        log_action(
            self.request.user, 'UPDATE_RECORD', 'MedicalRecord',
            str(record.id), request=self.request,
            extra={'patient_id': str(record.patient.id)}
        )

    def perform_destroy(self, instance):
        log_action(
            self.request.user, 'DELETE_RECORD', 'MedicalRecord',
            str(instance.id), request=self.request,
            extra={'patient_id': str(instance.patient.id)}
        )
        instance.delete()


class MedicalImageUploadView(generics.CreateAPIView):
    """
    Upload a medical image (DICOM, JPEG, PNG) attached to a record.
    - Validates MIME type via magic bytes
    - Strips metadata
    - Triggers async AI processing via Celery
    """
    serializer_class = MedicalImageSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        image = serializer.save()
        log_action(
            self.request.user, 'UPLOAD_IMAGE', 'MedicalImage',
            str(image.id), request=self.request,
            extra={'record_id': str(image.record.id)}
        )

    def create(self, request, *args, **kwargs):
        # Inject record_id from URL
        data = request.data.copy()
        data['record'] = kwargs.get('record_id')
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PatientRecordSummaryView(APIView):
    """Returns a summary of a patient's records (count by type)."""
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]

    def get(self, request, patient_id):
        from django.db.models import Count
        from apps.accounts.models import User

        try:
            patient = User.objects.get(id=patient_id, role=UserRole.PATIENT)
        except User.DoesNotExist:
            return Response({'error': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        summary = MedicalRecord.objects.filter(patient=patient).values('record_type').annotate(
            count=Count('id')
        )
        return Response({
            'patient': patient.get_full_name(),
            'total_records': MedicalRecord.objects.filter(patient=patient).count(),
            'by_type': list(summary),
        })
