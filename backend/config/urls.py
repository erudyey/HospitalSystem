"""URL configuration for HospitalSystem."""

import os

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import include, path


def serve_spa(request: HttpRequest) -> HttpResponse:
    """Serve the compiled Svelte single page application index.html with injected session token."""
    index_file = settings.FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return HttpResponse(
            """<!DOCTYPE html>
            <html>
            <head><title>HospitalSystem</title></head>
            <body style="font-family: sans-serif; padding: 40px; background: #fafafa; color: #09090b;">
                <h2>Frontend build not found</h2>
                <p>Please build the frontend application by running:</p>
                <pre style="background: #f4f4f5; padding: 12px; border-radius: 6px;">deno task build</pre>
                <p>or start the development server using <code>.\\run.ps1 dev</code>.</p>
            </body>
            </html>""",
            content_type="text/html",
            status=200,
        )

    html_content = index_file.read_text(encoding="utf-8")
    token = os.environ.get("HOSPITAL_SESSION_TOKEN", "")
    if token and "<head>" in html_content:
        injection = f'<script>window.__SESSION_TOKEN__ = "{token}";</script>'
        html_content = html_content.replace("<head>", f"<head>\n    {injection}", 1)

    response = HttpResponse(html_content, content_type="text/html")
    if token:
        response.set_cookie("session_token", token, samesite="Strict", httponly=True)
    return response


urlpatterns = [
    path("api/", include("backend.clinic.urls")),
    path("", serve_spa, name="spa-root"),
]
