"""URL configuration for HospitalSystem."""

import hmac
import json
import os

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def serve_spa(request: HttpRequest) -> HttpResponse:
    """Serve the compiled Svelte single page application index.html with injected session token."""
    token = os.environ.get("HOSPITAL_SESSION_TOKEN", "")
    provided = (
        request.GET.get("token", "")
        or request.headers.get("X-Session-Token", "")
        or request.COOKIES.get("session_token", "")
    )
    if (token and not hmac.compare_digest(provided, token)) or (not token and not settings.DEBUG):
        return HttpResponse("Open HospitalSystem through the desktop launcher.", status=403)
    index_file = settings.FRONTEND_DIST / "index.html"
    if not index_file.exists():
        html_content = """<!DOCTYPE html>
            <html>
            <head><title>HospitalSystem</title></head>
            <body style="font-family: sans-serif; padding: 40px; background: #fafafa; color: #09090b;">
                <h2>Frontend build not found</h2>
                <p>Please build the frontend application by running:</p>
                <pre style="background: #f4f4f5; padding: 12px; border-radius: 6px;">deno task build</pre>
                <p>or start the development server using <code>.\\run.ps1 dev</code>.</p>
            </body>
            </html>"""

    else:
        html_content = index_file.read_text(encoding="utf-8")
    if token and "<head>" in html_content:
        injection = (
            f"<script>window.__SESSION_TOKEN__ = {json.dumps(token)};"
            f"window.__DESKTOP_HOST__ = {json.dumps(os.environ.get('HOSPITAL_DESKTOP_HOST') == '1')};"
            "const launchUrl = new URL(window.location.href);"
            "launchUrl.searchParams.delete('token');"
            "history.replaceState(null, '', launchUrl);</script>"
        )
        html_content = html_content.replace("<head>", f"<head>\n    {injection}", 1)

    response = HttpResponse(html_content, content_type="text/html")
    if token:
        response.set_cookie("session_token", token, samesite="Strict", httponly=True)
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


urlpatterns = [
    path("api/", include("backend.clinic.urls")),
    path("", serve_spa, name="spa-root"),
]
