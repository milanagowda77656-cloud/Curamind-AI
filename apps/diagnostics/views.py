"""CuraMind AI - Diagnostics Views"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsDoctorOrRadiologist, IsDoctorOrNurse
from apps.audit.utils import log_action
from .models import DiagnosticResult
from .serializers import DiagnosticResultSerializer, DiagnosticReviewSerializer


class DiagnosticResultListView(generics.ListAPIView):
    """List diagnostic results. Scoped by role."""
    serializer_class = DiagnosticResultSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    filterset_fields = ['status']
    ordering_fields = ['anomaly_score', 'created_at']

    def get_queryset(self):
        from apps.accounts.models import UserRole
        user = self.request.user
        qs = DiagnosticResult.objects.select_related(
            'image__record__patient', 'image__record__doctor', 'reviewed_by'
        )
        if user.role == UserRole.DOCTOR:
            return qs.filter(image__record__doctor=user)
        elif user.role == UserRole.RADIOLOGIST:
            return qs.all()
        return qs.none()


class DiagnosticResultDetailView(generics.RetrieveUpdateAPIView):
    """Get full diagnostic result. Doctors/radiologists can add review notes."""
    permission_classes = [IsAuthenticated, IsDoctorOrRadiologist]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return DiagnosticReviewSerializer
        return DiagnosticResultSerializer

    def get_queryset(self):
        return DiagnosticResult.objects.select_related(
            'image__record__patient', 'image__record__doctor', 'reviewed_by'
        )

    def perform_update(self, serializer):
        result = serializer.save(
            reviewed_by=self.request.user,
            reviewed_at=timezone.now()
        )
        log_action(
            self.request.user, 'REVIEW_DIAGNOSTIC', 'DiagnosticResult',
            str(result.id), request=self.request
        )


class HighRiskResultsView(generics.ListAPIView):
    """List all high-risk (score >= 0.7) unreviewed diagnostics."""
    serializer_class = DiagnosticResultSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrRadiologist]

    def get_queryset(self):
        return DiagnosticResult.objects.filter(
            anomaly_score__gte=0.7,
            reviewed_by__isnull=True
        ).select_related('image__record__patient', 'image__record__doctor')


class RetriggerAnalysisView(APIView):
    """Manually retrigger AI analysis for a specific image."""
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]

    def post(self, request, image_id):
        from apps.medical_records.models import MedicalImage
        from .tasks import process_medical_image

        try:
            image = MedicalImage.objects.get(id=image_id)
        except MedicalImage.DoesNotExist:
            return Response({'error': 'Image not found.'}, status=status.HTTP_404_NOT_FOUND)

        process_medical_image.delay(str(image.id))
        log_action(request.user, 'RETRIGGER_ANALYSIS', 'MedicalImage', str(image_id), request=request)
        return Response({'message': 'Analysis re-queued successfully.'})
