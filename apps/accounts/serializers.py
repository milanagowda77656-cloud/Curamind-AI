"""CuraMind AI - Accounts Serializers"""

from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, DoctorProfile, PatientProfile, PasswordResetToken, UserRole


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extended JWT serializer that includes user role and name in token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.get_full_name()
        token['email'] = user.email
        return token


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ('user',)


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ('user',)


class UserSerializer(serializers.ModelSerializer):
    """Full user serializer. Sensitive fields are write-only."""

    doctor_profile = DoctorProfileSerializer(read_only=True)
    patient_profile = PatientProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone_number', 'date_of_birth', 'profile_picture',
            'license_number', 'specialization', 'department',
            'is_active', 'is_email_verified', 'date_joined',
            'doctor_profile', 'patient_profile',
        ]
        read_only_fields = ('id', 'date_joined', 'is_email_verified')

    def get_full_name(self, obj):
        return obj.get_full_name()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=10)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role',
            'phone_number', 'date_of_birth',
            'license_number', 'specialization',  # Doctor fields
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})

        # Doctors must provide license number
        if attrs.get('role') == UserRole.DOCTOR and not attrs.get('license_number'):
            raise serializers.ValidationError({'license_number': 'Doctors must provide a license number.'})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Auto-create profile based on role
        if user.role == UserRole.DOCTOR:
            DoctorProfile.objects.create(user=user)
        elif user.role == UserRole.PATIENT:
            PatientProfile.objects.create(user=user)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=10)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(min_length=10)
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class DoctorListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing doctors (used by patients)."""

    full_name = serializers.SerializerMethodField()
    doctor_profile = DoctorProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'specialization', 'department', 'doctor_profile']

    def get_full_name(self, obj):
        return obj.get_full_name()
