from django.urls import path
from .views import AuditLogListView, PatientAuditLogView

urlpatterns = [
    path('', AuditLogListView.as_view(), name='audit_log_list'),
    path('patient/<uuid:patient_id>/', PatientAuditLogView.as_view(), name='patient_audit_log'),
]
