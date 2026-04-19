from django.urls import path
from .views import (
    DiagnosticResultListView, DiagnosticResultDetailView,
    HighRiskResultsView, RetriggerAnalysisView,
)

urlpatterns = [
    path('', DiagnosticResultListView.as_view(), name='diagnostic_list'),
    path('<uuid:pk>/', DiagnosticResultDetailView.as_view(), name='diagnostic_detail'),
    path('high-risk/', HighRiskResultsView.as_view(), name='high_risk_results'),
    path('retrigger/<uuid:image_id>/', RetriggerAnalysisView.as_view(), name='retrigger_analysis'),
]
