from django.urls import path
from .views import (
    AppointmentListCreateView, AppointmentDetailView,
    DoctorAvailabilityView, UpcomingAppointmentsView,
)

urlpatterns = [
    path('', AppointmentListCreateView.as_view(), name='appointment_list_create'),
    path('<uuid:pk>/', AppointmentDetailView.as_view(), name='appointment_detail'),
    path('upcoming/', UpcomingAppointmentsView.as_view(), name='upcoming_appointments'),
    path('doctor/<uuid:doctor_id>/availability/', DoctorAvailabilityView.as_view(), name='doctor_availability'),
]
