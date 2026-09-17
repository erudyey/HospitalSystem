"""URL configuration for HospitalSystem."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import include, path


def serve_spa(_request: HttpRequest) -> HttpResponse:
    """Serve the compiled Svelte single page application index.html."""
    index_file = settings.FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return HttpResponse(
            """<!DOCTYPE html>
            <html>
            <head><title>HospitalSystem</title></head>
            <body style="font-family: sans-serif; padding: 40px; background: #faf9f6; color: #1c1917;">
                <h2>Frontend build not found</h2>
                <p>Please build the frontend application by running:</p>
                <pre style="background: #e7e5e4; padding: 12px; border-radius: 6px;">deno task build</pre>
                <p>or start the development server using <code>.\\run.ps1 dev</code>.</p>
            </body>
            </html>""",
            content_type="text/html",
            status=200,
        )
    return HttpResponse(index_file.read_bytes(), content_type="text/html")


urlpatterns = [
    path("api/", include("backend.clinic.urls")),
    path("", serve_spa, name="spa-root"),
]
