"""CuraMind AI - Accounts Views"""

import logging
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetToken, UserRole
from .serializers import (
    CustomTokenObtainPairSerializer, RegisterSerializer, UserSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, DoctorListSerializer,
)
from apps.audit.utils import log_action

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT login endpoint with role info embedded in token."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                user = User.objects.get(email=request.data.get('email'))
                user.last_login_ip = request.META.get('REMOTE_ADDR')
                user.save(update_fields=['last_login_ip'])
                log_action(user, 'LOGIN', 'User', str(user.id), request=request)
            except User.DoesNotExist:
                pass
        return response


class RegisterView(generics.CreateAPIView):
    """Register a new user (patient, doctor, nurse)."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(user, 'REGISTER', 'User', str(user.id), request=request)
        return Response(
            {'message': 'Account created successfully. Please verify your email.', 'user_id': str(user.id)},
            status=status.HTTP_201_CREATED
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        log_action(request.user, 'UPDATE_PROFILE', 'User', str(request.user.id), request=request)
        return response


class ChangePasswordView(APIView):
    """Change password for authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        log_action(user, 'CHANGE_PASSWORD', 'User', str(user.id), request=request)
        return Response({'message': 'Password changed successfully.'})


class PasswordResetRequestView(APIView):
    """Request a password reset email."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1)
            )
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{token.token}"

            send_mail(
                subject='CuraMind AI - Password Reset Request',
                message=f'Click the link to reset your password: {reset_url}\n\nLink expires in 1 hour.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response({'message': 'If the email is registered, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    """Confirm password reset with token."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = PasswordResetToken.objects.get(token=serializer.validated_data['token'])
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not token_obj.is_valid():
            return Response({'error': 'Token has expired or already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        token_obj.used = True
        token_obj.save()

        log_action(user, 'PASSWORD_RESET', 'User', str(user.id), request=request)
        return Response({'message': 'Password reset successfully.'})


class LogoutView(APIView):
    """Blacklist JWT refresh token on logout."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_action(request.user, 'LOGOUT', 'User', str(request.user.id), request=request)
            return Response({'message': 'Logged out successfully.'})
        except Exception:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class DoctorListView(generics.ListAPIView):
    """List all available doctors - accessible to patients."""
    serializer_class = DoctorListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['specialization', 'department']
    search_fields = ['first_name', 'last_name', 'specialization']

    def get_queryset(self):
        return User.objects.filter(
            role=UserRole.DOCTOR,
            is_active=True
        ).select_related('doctor_profile')
