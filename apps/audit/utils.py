"""CuraMind AI - Audit Utility Functions"""

import logging

logger = logging.getLogger(__name__)


def log_action(user, action: str, resource_type: str, resource_id: str = '',
               request=None, extra: dict = None):
    """
    Convenience function to create an AuditLog entry.
    Call this from any view or service that touches sensitive data.

    Args:
        user:          The User performing the action (can be None for anon).
        action:        AuditAction choice string (e.g. 'VIEW_RECORD').
        resource_type: The model/object type affected (e.g. 'MedicalRecord').
        resource_id:   The UUID or identifier of the affected object.
        request:       The DRF/Django request object (for IP and user-agent).
        extra:         Additional context dict (e.g. {'patient_id': '...'}).
    """
    from .models import AuditLog

    try:
        ip_address = None
        user_agent = ''

        if request:
            # Handle proxied IP (e.g. behind Nginx)
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded:
                ip_address = x_forwarded.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra or {},
        )
    except Exception as e:
        # Audit failures must never break the main flow — log and continue
        logger.error(f'[log_action] Failed to write audit log: {e}', exc_info=True)
