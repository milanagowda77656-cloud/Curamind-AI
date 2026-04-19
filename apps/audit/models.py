"""
CuraMind AI - Audit Models
HIPAA-compliant immutable audit log.
Every access/edit/delete on sensitive data is recorded here.
Records are write-once — no update/delete allowed.
"""

import uuid
from django.db import models


class AuditAction(models.TextChoices):
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    REGISTER = 'REGISTER', 'Register'
    VIEW_RECORD = 'VIEW_RECORD', 'View Medical Record'
    CREATE_RECORD = 'CREATE_RECORD', 'Create Medical Record'
    UPDATE_RECORD = 'UPDATE_RECORD', 'Update Medical Record'
    DELETE_RECORD = 'DELETE_RECORD', 'Delete Medical Record'
    UPLOAD_IMAGE = 'UPLOAD_IMAGE', 'Upload Medical Image'
    REVIEW_DIAGNOSTIC = 'REVIEW_DIAGNOSTIC', 'Review Diagnostic Result'
    RETRIGGER_ANALYSIS = 'RETRIGGER_ANALYSIS', 'Retrigger AI Analysis'
    CREATE_APPOINTMENT = 'CREATE_APPOINTMENT', 'Create Appointment'
    UPDATE_APPOINTMENT = 'UPDATE_APPOINTMENT', 'Update Appointment'
    UPDATE_PROFILE = 'UPDATE_PROFILE', 'Update Profile'
    CHANGE_PASSWORD = 'CHANGE_PASSWORD', 'Change Password'
    PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
    PERMISSION_DENIED = 'PERMISSION_DENIED', 'Permission Denied'
    SUSPICIOUS_ACTIVITY = 'SUSPICIOUS_ACTIVITY', 'Suspicious Activity'


class AuditLog(models.Model):
    """
    Immutable audit log entry.
    Created programmatically — never updated or deleted.
    Used for HIPAA compliance validation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    resource_type = models.CharField(max_length=100)  # e.g. 'MedicalRecord'
    resource_id = models.CharField(max_length=255, blank=True)  # UUID of the affected object
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)  # Additional context
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
        # Prevent updates and deletes at DB level via app logic
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'

    def __str__(self):
        user_str = self.user.email if self.user else 'Anonymous'
        return f'[{self.timestamp}] {user_str} → {self.action} on {self.resource_type}'

    def save(self, *args, **kwargs):
        # Enforce immutability: only allow INSERT, never UPDATE
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError('Audit log entries are immutable and cannot be modified.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit log entries cannot be deleted.')
