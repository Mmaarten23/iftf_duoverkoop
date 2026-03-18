"""Middleware helpers for production diagnostics."""
import logging

from django.http import HttpResponse

from iftf_duoverkoop.src.core.models import DatabaseOperation

logger = logging.getLogger("iftf_duoverkoop.request")


class RequestExceptionLoggingMiddleware:
    """
    Log request context when an unhandled exception bubbles up.

    Django still returns its normal 500 response; this only enriches logs so
    Render shows enough context to debug quickly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception:
            user = getattr(request, "user", None)
            user_repr = (
                user.get_username() if getattr(user, "is_authenticated", False) else "anonymous"
            )
            xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
            ip = (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown"))
            logger.exception(
                "Unhandled exception. method=%s path=%s user=%s ip=%s",
                request.method,
                request.path,
                user_repr,
                ip,
            )
            raise


class RestoreMaintenanceLockMiddleware:
    """Block write requests while a restore is running to avoid inconsistent state."""

    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    ALLOWED_PREFIXES = (
        '/dashboard/system',
        '/admin/',
        '/static/',
        '/media/',
        '/login/',
        '/logout/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in self.SAFE_METHODS:
            return self.get_response(request)
        if request.path.startswith(self.ALLOWED_PREFIXES):
            return self.get_response(request)

        try:
            restore_running = DatabaseOperation.objects.filter(
                operation_type=DatabaseOperation.TYPE_RESTORE,
                status__in=[DatabaseOperation.STATUS_QUEUED, DatabaseOperation.STATUS_RUNNING],
            ).exists()
        except Exception:
            # Do not block traffic if the lock check itself fails.
            restore_running = False

        if restore_running:
            return HttpResponse(
                'Database maintenance is in progress. Please retry shortly.',
                status=503,
                content_type='text/plain; charset=utf-8',
            )

        return self.get_response(request)


