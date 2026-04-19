"""
CuraMind AI - Audit Middleware
Automatically logs 403/401 responses as PERMISSION_DENIED audit events.
"""

import logging

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """
    Middleware that intercepts 403/401 responses and logs them as audit events.
    This catches permission denials that may not be explicitly logged in views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code in [401, 403]:
            try:
                from .utils import log_action
                user = getattr(request, 'user', None)
                log_action(
                    user=user if user and user.is_authenticated else None,
                    action='PERMISSION_DENIED',
                    resource_type='HTTP',
                    resource_id=request.path,
                    request=request,
                    extra={'status_code': response.status_code, 'method': request.method}
                )
            except Exception as e:
                logger.error(f'[AuditLogMiddleware] Failed to log permission denial: {e}')

        return response
