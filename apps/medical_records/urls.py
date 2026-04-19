from django.urls import path
from .views import (
    MedicalRecordListCreateView, MedicalRecordDetailView,
    MedicalImageUploadView, PatientRecordSummaryView,
)

urlpatterns = [
    path('', MedicalRecordListCreateView.as_view(), name='record_list_create'),
    path('<uuid:pk>/', MedicalRecordDetailView.as_view(), name='record_detail'),
    path('<uuid:record_id>/images/', MedicalImageUploadView.as_view(), name='image_upload'),
    path('patient/<uuid:patient_id>/summary/', PatientRecordSummaryView.as_view(), name='patient_summary'),
]
