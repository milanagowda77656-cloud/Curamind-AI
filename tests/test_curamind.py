"""
CuraMind AI - Test Suite
Covers: Auth, RBAC, Medical Records, Audit Log
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.medical_records.models import MedicalRecord, RecordType
from apps.audit.models import AuditLog
from tests.factories import (
    PatientFactory, DoctorFactory, NurseFactory, AdminFactory,
    AppointmentFactory, MedicalRecordFactory, AuditLogFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def patient(db):
    return PatientFactory()


@pytest.fixture
def doctor(db):
    return DoctorFactory()


@pytest.fixture
def nurse(db):
    return NurseFactory()


@pytest.fixture
def admin(db):
    return AdminFactory()


@pytest.fixture
def patient_client(api_client, patient):
    api_client.force_authenticate(user=patient)
    return api_client


@pytest.fixture
def doctor_client(api_client, doctor):
    api_client.force_authenticate(user=doctor)
    return api_client


@pytest.fixture
def nurse_client(api_client, nurse):
    api_client.force_authenticate(user=nurse)
    return api_client


@pytest.fixture
def admin_client(api_client, admin):
    api_client.force_authenticate(user=admin)
    return api_client


# ──────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuthentication:

    def test_register_patient_success(self, api_client):
        """Patients can register with valid data."""
        url = reverse('register')
        data = {
            'email': 'newpatient@test.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'role': UserRole.PATIENT,
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='newpatient@test.com').exists()

    def test_register_doctor_requires_license(self, api_client):
        """Doctor registration fails without license number."""
        url = reverse('register')
        data = {
            'email': 'dr.nolicense@test.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'first_name': 'Dr',
            'last_name': 'No License',
            'role': UserRole.DOCTOR,
            # No license_number provided
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'license_number' in response.data

    def test_register_password_mismatch(self, api_client):
        """Registration fails if passwords don't match."""
        url = reverse('register')
        data = {
            'email': 'test@test.com',
            'password': 'StrongPass123!',
            'password_confirm': 'DifferentPass!',
            'first_name': 'Test',
            'last_name': 'User',
            'role': UserRole.PATIENT,
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_returns_jwt(self, api_client, patient):
        """Login returns access and refresh JWT tokens."""
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {'email': patient.email, 'password': 'TestPass1234!'})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_unauthenticated_access_denied(self, api_client):
        """Unauthenticated requests to protected endpoints are rejected."""
        url = reverse('record_list_create')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_own_profile(self, patient_client):
        """Authenticated user can retrieve their own profile."""
        url = reverse('profile')
        response = patient_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'email' in response.data


# ──────────────────────────────────────────────────────────
# RBAC Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRBAC:

    def test_patient_cannot_create_medical_record(self, patient_client, patient, doctor):
        """Patients cannot create medical records — only doctors can."""
        url = reverse('record_list_create')
        data = {
            'patient': str(patient.id),
            'record_type': RecordType.CONSULTATION,
            'title': 'Patient-created record',
        }
        response = patient_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_cannot_view_patient_records(self, admin_client):
        """Admins are blocked from viewing private patient medical data (HIPAA)."""
        url = reverse('record_list_create')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0  # Admin sees zero records

    def test_nurse_has_read_only_access(self, nurse_client, doctor, patient):
        """Nurses can list records but cannot create them."""
        url = reverse('record_list_create')
        # Read: allowed
        response = nurse_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Create: denied
        data = {
            'patient': str(patient.id),
            'record_type': RecordType.LAB_RESULT,
            'title': 'Nurse-created record',
        }
        response = nurse_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patient_can_only_view_own_records(self, db, api_client):
        """Patients cannot view other patients' records."""
        patient_a = PatientFactory()
        patient_b = PatientFactory()
        doctor = DoctorFactory()

        # Link patient_b to doctor
        patient_b.patient_profile.primary_doctor = doctor
        patient_b.patient_profile.save()

        record = MedicalRecordFactory(patient=patient_b, doctor=doctor)

        api_client.force_authenticate(user=patient_a)
        url = reverse('record_detail', kwargs={'pk': record.id})
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_doctor_can_access_patient_records(self, db, api_client):
        """Doctors can access their own patients' records."""
        doctor = DoctorFactory()
        patient = PatientFactory()
        patient.patient_profile.primary_doctor = doctor
        patient.patient_profile.save()

        record = MedicalRecordFactory(patient=patient, doctor=doctor)

        api_client.force_authenticate(user=doctor)
        url = reverse('record_detail', kwargs={'pk': record.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK


# ──────────────────────────────────────────────────────────
# Medical Records Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMedicalRecords:

    def test_encryption_at_rest(self, db):
        """Sensitive fields are stored encrypted in the database."""
        doctor = DoctorFactory()
        patient = PatientFactory()
        record = MedicalRecord(
            patient=patient,
            doctor=doctor,
            record_type=RecordType.CONSULTATION,
            title='Encryption Test',
        )
        raw_diagnosis = 'Type 2 Diabetes Mellitus'
        record.diagnosis = raw_diagnosis
        record.save()

        # Read raw DB value — should NOT equal the plain text
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT diagnosis FROM medical_records_medicalrecord WHERE id = %s', [str(record.id)])
            raw_db_value = cursor.fetchone()[0]

        assert raw_db_value != raw_diagnosis, 'Diagnosis should be encrypted in DB'
        assert record.diagnosis == raw_diagnosis, 'Decrypted value should match original'

    def test_doctor_creates_record(self, db, api_client):
        """Doctors can successfully create medical records."""
        doctor = DoctorFactory()
        patient = PatientFactory()
        patient.patient_profile.primary_doctor = doctor
        patient.patient_profile.save()

        api_client.force_authenticate(user=doctor)
        url = reverse('record_list_create')
        data = {
            'patient': str(patient.id),
            'record_type': RecordType.CONSULTATION,
            'title': 'Annual Check-up',
            'diagnosis': 'Healthy',
            'notes': 'No concerns found.',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert MedicalRecord.objects.filter(patient=patient).exists()

    def test_record_access_creates_audit_log(self, db, api_client):
        """Viewing a medical record creates an immutable audit log entry."""
        doctor = DoctorFactory()
        patient = PatientFactory()
        patient.patient_profile.primary_doctor = doctor
        patient.patient_profile.save()

        record = MedicalRecordFactory(patient=patient, doctor=doctor)

        api_client.force_authenticate(user=doctor)
        url = reverse('record_detail', kwargs={'pk': record.id})
        api_client.get(url)

        assert AuditLog.objects.filter(
            action='VIEW_RECORD',
            resource_id=str(record.id)
        ).exists()

    def test_audit_log_is_immutable(self, db):
        """Audit log entries cannot be modified after creation."""
        log = AuditLogFactory()
        with pytest.raises(PermissionError):
            log.action = 'MODIFIED_ACTION'
            log.save()

    def test_audit_log_cannot_be_deleted(self, db):
        """Audit log entries cannot be deleted."""
        log = AuditLogFactory()
        with pytest.raises(PermissionError):
            log.delete()


# ──────────────────────────────────────────────────────────
# Appointment Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAppointments:

    def test_patient_can_book_appointment(self, patient_client, doctor):
        """Patients can book an appointment with a doctor."""
        from django.utils import timezone
        from datetime import timedelta
        url = reverse('appointment_list_create')
        data = {
            'doctor': str(doctor.id),
            'appointment_type': 'GENERAL',
            'scheduled_at': (timezone.now() + timedelta(days=5)).isoformat(),
            'reason': 'Routine check-up',
        }
        response = patient_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_cannot_book_past_appointment(self, patient_client, doctor):
        """Cannot book an appointment in the past."""
        from django.utils import timezone
        from datetime import timedelta
        url = reverse('appointment_list_create')
        data = {
            'doctor': str(doctor.id),
            'appointment_type': 'GENERAL',
            'scheduled_at': (timezone.now() - timedelta(days=1)).isoformat(),
            'reason': 'Past appointment attempt',
        }
        response = patient_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_doctor_sees_their_appointments(self, doctor_client, doctor, patient):
        """Doctors can list only their own appointments."""
        AppointmentFactory(doctor=doctor, patient=patient)
        other_doctor = DoctorFactory()
        AppointmentFactory(doctor=other_doctor, patient=patient)

        url = reverse('appointment_list_create')
        response = doctor_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        for appt in response.data['results']:
            assert appt['doctor'] == str(doctor.id)
