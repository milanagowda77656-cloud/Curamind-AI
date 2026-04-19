"""
CuraMind AI - Test Factories
Uses factory_boy for consistent, realistic test data generation.
"""

import factory
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User, UserRole, DoctorProfile, PatientProfile
from apps.appointments.models import Appointment, AppointmentType, AppointmentStatus
from apps.medical_records.models import MedicalRecord, RecordType
from apps.audit.models import AuditLog


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@curamind.test')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = UserRole.PATIENT
    is_active = True
    is_email_verified = True
    password = factory.PostGenerationMethodCall('set_password', 'TestPass1234!')


class DoctorFactory(UserFactory):
    role = UserRole.DOCTOR
    specialization = factory.Faker('job')
    department = 'Radiology'
    license_number = factory.Sequence(lambda n: f'LIC-{n:05d}')
    email = factory.Sequence(lambda n: f'doctor{n}@curamind.test')

    @factory.post_generation
    def create_profile(obj, create, extracted, **kwargs):
        if create:
            DoctorProfile.objects.get_or_create(user=obj)


class PatientFactory(UserFactory):
    role = UserRole.PATIENT
    email = factory.Sequence(lambda n: f'patient{n}@curamind.test')

    @factory.post_generation
    def create_profile(obj, create, extracted, **kwargs):
        if create:
            PatientProfile.objects.get_or_create(user=obj)


class NurseFactory(UserFactory):
    role = UserRole.NURSE
    email = factory.Sequence(lambda n: f'nurse{n}@curamind.test')


class AdminFactory(UserFactory):
    role = UserRole.ADMIN
    is_staff = True
    email = factory.Sequence(lambda n: f'admin{n}@curamind.test')


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment

    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    appointment_type = AppointmentType.GENERAL
    status = AppointmentStatus.PENDING
    scheduled_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=3))
    duration_minutes = 30
    reason = factory.Faker('sentence')


class MedicalRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MedicalRecord

    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    record_type = RecordType.CONSULTATION
    title = factory.Faker('sentence', nb_words=4)
    is_critical = False
    follow_up_required = False

    class Params:
        raw_diagnosis = 'Test diagnosis'
        raw_notes = 'Test clinical notes'
        raw_prescription = 'Test prescription'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = model_class(*args, **kwargs)
        obj.diagnosis = kwargs.get('raw_diagnosis', 'Default diagnosis')
        obj.notes = kwargs.get('raw_notes', 'Default notes')
        obj.prescription = kwargs.get('raw_prescription', 'Default prescription')
        obj.save()
        return obj


class AuditLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditLog

    user = factory.SubFactory(PatientFactory)
    action = 'VIEW_RECORD'
    resource_type = 'MedicalRecord'
    resource_id = factory.Sequence(lambda n: str(n))
    ip_address = '127.0.0.1'
