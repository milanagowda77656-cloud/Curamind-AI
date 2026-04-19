from django.contrib import admin
from .models import Appointment, AppointmentSlot


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'scheduled_at', 'status', 'appointment_type')
    list_filter = ('status', 'appointment_type')
    search_fields = ('patient__email', 'doctor__email', 'reason')
    ordering = ('-scheduled_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'start_time', 'end_time', 'is_booked')
    list_filter = ('is_booked', 'date')
    search_fields = ('doctor__email',)
