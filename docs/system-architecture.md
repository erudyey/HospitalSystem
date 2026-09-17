# System architecture and technical specifications

This document outlines the runtime lifecycle, process boundaries, and design layers of the Hospital Management System.

---

## 1. Architectural layers and boundaries

```text
+-------------------------------------------------------------------------+
|                  pywebview Native Desktop Window (Win32)                 |
|  +-------------------------------------------------------------------+  |
|  |             Svelte Single Page Application (shadcn-svelte)         |  |
|  +-------------------------------------------------------------------+  |
+------------------------------------|------------------------------------+
                                     | HTTP Requests (127.0.0.1 loopback)
                                     | Header: X-Session-Token or Strict Cookie
                                     v
+-------------------------------------------------------------------------+
|                    Waitress Production WSGI Server                       |
|  +-------------------------------------------------------------------+  |
|  |                    WhiteNoise Static Asset Host                   |  |
|  +-------------------------------------------------------------------+  |
|  |                  Django Request and Response Stack                |  |
|  |                                                                   |  |
|  |  [Security Token Middleware]  ->  Validates per-launch token       |  |
|  |  [JSON API Views]             ->  Thin HTTP and error serialization|  |
|  |  [Python Services Layer]      ->  Pure business validation & logic |  |
|  |  [Django ORM]                 ->  Strongly typed models & atomic TX|  |
|  +-------------------------------------------------------------------+  |
+------------------------------------|------------------------------------+
                                     | SQLite WAL (Write-Ahead Logging)
                                     v
+-------------------------------------------------------------------------+
|         %LOCALAPPDATA%\HospitalSystem\clinic.sqlite3                    |
+-------------------------------------------------------------------------+
```

---

## 2. Desktop lifecycle and process management

The application runs as a local Windows desktop program through `desktop/launcher.py`. Its startup sequence follows these steps:

1. **Single-instance Windows mutex**:
   `CreateMutexW` checks for an existing `Local\HospitalSystem_AppMutex`. If one is already registered, the launcher warns the user with a native Windows message box and exits immediately, preventing conflicting SQLite locks.
2. **Ephemeral port pre-binding**:
   The launcher pre-binds an ephemeral socket on `127.0.0.1:0`. The operating system allocates an available port, which is immediately reserved and handed to Waitress, avoiding check-then-bind race conditions.
3. **Loopback server startup**:
   Waitress starts inside a background daemon thread. A 256-bit unguessable session token is generated using Python's `secrets.token_urlsafe(32)`.
4. **Readiness probe**:
   The launcher polls `http://127.0.0.1:{port}/api/health/` until HTTP 200 is confirmed, with an 8-second safety timeout.
5. **Window launch and token handoff**:
   The launcher opens pywebview using the Microsoft Edge WebView2 runtime, pointing to `http://127.0.0.1:{port}/?token={session_token}`. The Django root handler verifies this initial token, synchronously embeds `<script>window.__SESSION_TOKEN__ = '{token}';</script>` into the HTML `<head>`, sets a `SameSite=Strict` cookie, and scrubs the query string from the window URL with `history.replaceState`. This guarantees the token is available before any Svelte component mounts.
6. **Graceful shutdown**:
   When the user closes the window, pywebview's `closing` event and Python's `atexit` hooks fire, closing the server socket and stopping the background thread cleanly.

---

## 3. Local security model

1. **Loopback isolation**:
   Waitress binds exclusively to IPv4 `127.0.0.1`. It never listens on `0.0.0.0` or local network interfaces, so Windows Defender Firewall never prompts for incoming network permissions.
2. **Session token verification**:
   `LoopbackSecurityMiddleware` intercepts incoming `/api/` calls. Requests without a valid `X-Session-Token` header or matching strict cookie receive an immediate HTTP 403 Forbidden. Constant-time comparison via `hmac.compare_digest` prevents timing side-channels.
3. **CSRF protection**:
   Django's CSRF middleware runs on all mutating endpoints (`POST`, `PATCH`), requiring the standard `X-CSRFToken` header.

---

## 4. Pure Python service layer

Business logic lives strictly in `backend/clinic/services.py`:
- **Views are thin adapters**: `clinic.views` only parses JSON, invokes the appropriate service function, and maps returns to JSON HTTP responses.
- **Services are framework-independent Python functions**:
  - Validates models explicitly with `model.full_clean()` before saving.
  - Wraps all write operations inside `transaction.atomic()`.
  - Accepts and returns standard Python types and model instances, never Django `HttpRequest` or `HttpResponse` objects.
  - Can be tested directly in unit tests without starting an HTTP server.

---

## 5. Persistence and database storage

- **Production path**: `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`.
- **Test path**: In-memory database (`:memory:`) or isolated temporary directory per test run.
- **Concurrency settings**:
  - `PRAGMA journal_mode = WAL;` (Write-Ahead Logging) permits concurrent reads while a write transaction is active, avoiding lock errors on Windows.
  - `PRAGMA foreign_keys = ON;` enforces relational integrity between patients and appointments.
