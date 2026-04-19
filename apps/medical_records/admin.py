from django.contrib import admin
from .models import MedicalRecord, MedicalImage


class MedicalImageInline(admin.TabularInline):
    model = MedicalImage
    extra = 0
    readonly_fields = ('id', 'original_filename', 'mime_type', 'file_size_bytes', 'ai_processed', 'uploaded_at')


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'record_type', 'title', 'is_critical', 'created_at')
    list_filter = ('record_type', 'is_critical', 'follow_up_required')
    search_fields = ('patient__email', 'doctor__email', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [MedicalImageInline]

    def get_queryset(self, request):
        # Admins cannot view private patient medical data (HIPAA)
        if not request.user.is_superuser:
            return super().get_queryset(request).none()
        return super().get_queryset(request)


@admin.register(MedicalImage)
class MedicalImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'record', 'original_filename', 'is_dicom', 'ai_processed', 'uploaded_at')
    list_filter = ('is_dicom', 'ai_processed')
    readonly_fields = ('id', 'uploaded_at', 'mime_type', 'file_size_bytes')
