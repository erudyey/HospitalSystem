"""Loopback security token verification middleware."""

import hmac
import os
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse


class LoopbackSecurityMiddleware:
    """Validate per-launch X-Session-Token header on all API endpoints."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only enforce on /api/ endpoints, excluding /api/health/ readiness check
        if request.path.startswith("/api/") and request.path != "/api/health/":
            session_token = os.environ.get("HOSPITAL_SESSION_TOKEN")

            # Allow dev bypass if DEBUG is True and no token is set in environment
            if settings.DEBUG and not session_token:
                return self.get_response(request)

            provided_token = request.headers.get("X-Session-Token", "") or request.COOKIES.get(
                "session_token", ""
            )
            if not session_token or not hmac.compare_digest(provided_token, session_token):
                return JsonResponse(
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Missing or invalid session security token.",
                            "fields": {},
                        }
                    },
                    status=403,
                )

        return self.get_response(request)
