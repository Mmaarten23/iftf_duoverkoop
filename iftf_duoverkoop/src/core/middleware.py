"""Middleware helpers for production diagnostics."""
import logging

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

