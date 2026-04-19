"""
CuraMind AI - RBAC Permissions
Granular role-based access control as per HIPAA requirements.
"""

from rest_framework.permissions import BasePermission
from .models import UserRole


class IsDoctor(BasePermission):
    """Only doctors can access this resource."""
    message = 'Access restricted to verified doctors.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.DOCTOR)


class IsPatient(BasePermission):
    """Only patients can access this resource."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.PATIENT)


class IsNurse(BasePermission):
    """Only nurses can access this resource."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.NURSE)


class IsAdminUser(BasePermission):
    """Only admins can access this resource."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN)


class IsRadiologist(BasePermission):
    """Only radiologists can access this resource."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.RADIOLOGIST)


class IsDoctorOrNurse(BasePermission):
    """Doctors and nurses can access this resource."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [UserRole.DOCTOR, UserRole.NURSE]
        )


class IsDoctorOrRadiologist(BasePermission):
    """Doctors and radiologists can access diagnostic results."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [UserRole.DOCTOR, UserRole.RADIOLOGIST]
        )


class IsOwnerOrDoctor(BasePermission):
    """
    Object-level: Patient can access their own data.
    Doctor can access their assigned patient's data.
    Nurses have read-only access.
    Admins CANNOT view private patient medical data (HIPAA separation).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin cannot view private patient medical data
        if user.role == UserRole.ADMIN:
            return False

        # Patient can only access their own data
        if user.role == UserRole.PATIENT:
            patient = getattr(obj, 'patient', None)
            if patient:
                return patient == user
            return obj == user

        # Doctors can access their patients' data
        if user.role == UserRole.DOCTOR:
            patient = getattr(obj, 'patient', None)
            if patient and hasattr(patient, 'patient_profile'):
                return patient.patient_profile.primary_doctor == user
            return True  # Doctor can view other records

        # Nurses have read-only access to medical records
        if user.role == UserRole.NURSE:
            return request.method in ['GET', 'HEAD', 'OPTIONS']

        # Radiologists can view imaging records
        if user.role == UserRole.RADIOLOGIST:
            return True

        return False
