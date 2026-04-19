from django.contrib import admin
from .models import DiagnosticResult, DiagnosticQueue


@admin.register(DiagnosticResult)
class DiagnosticResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'status', 'anomaly_score', 'confidence', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('image__original_filename',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'processing_time_ms')


@admin.register(DiagnosticQueue)
class DiagnosticQueueAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'celery_task_id', 'queued_at', 'completed_at', 'retries')
    readonly_fields = ('id', 'queued_at')
