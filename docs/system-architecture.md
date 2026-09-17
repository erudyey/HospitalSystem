# System Architecture & Technical Specifications

This document defines the runtime lifecycle, security boundaries, and architectural layers of the modernized Hospital Management System.

---

## 1. Architectural Layers & Boundaries

```text
+-------------------------------------------------------------------------+
|                  pywebview Native Desktop Window (Win32)                 |
|  +-------------------------------------------------------------------+  |
|  |             Svelte Single Page Application (shadcn-svelte)         |  |
|  +-------------------------------------------------------------------+  |
+------------------------------------|------------------------------------+
                                     | HTTP Requests (127.0.0.1 loopback)
                                     | Header: X-Session-Token
                                     v
+-------------------------------------------------------------------------+
|                    Waitress Production WSGI Server                       |
|  +-------------------------------------------------------------------+  |
|  |                    WhiteNoise Static Asset Host                   |  |
|  +-------------------------------------------------------------------+  |
|  |                  Django Request / Response Stack                  |  |
|  |                                                                   |  |
|  |  [Security Token Middleware]  ->  Validates Session Token         |  |
|  |  [JSON API Views]             ->  Thin HTTP & Error Serialization |  |
|  |  [Python Services Layer]      ->  Pure Business Validation & Logic|  |
|  |  [Django ORM]                 ->  Models & Transactions           |  |
|  +-------------------------------------------------------------------+  |
+------------------------------------|------------------------------------+
                                     | SQLite WAL (Write-Ahead Logging)
                                     v
+-------------------------------------------------------------------------+
|         %LOCALAPPDATA%\HospitalSystem\clinic.sqlite3                    |
+-------------------------------------------------------------------------+
```

---

## 2. Desktop Lifecycle & Process Orchestration

The desktop application execution lifecycle follows a strict sequence in `desktop/launcher.py`:

1. **Single-Instance Win32 Mutex**:
   - `CreateMutexW(None, False, "Local\\HospitalSystem_AppMutex")` guarantees only one instance runs. If a mutex exists, the previous window is focused and the new process terminates cleanly.
2. **Ephemeral Port Pre-Binding**:
   - Rather than checking a port and later binding it (susceptible to race conditions), an ephemeral socket binds `127.0.0.1:0`. The OS allocates an unused port, which is immediately reserved and handed to Waitress.
3. **Loopback Server Launch**:
   - Waitress starts inside a background daemon thread (`daemon=True`).
   - A 256-bit cryptographically secure session token (`secrets.token_urlsafe(32)`) is generated in memory.
4. **Readiness Probe**:
   - The launcher polls `GET http://127.0.0.1:{port}/api/health/` until HTTP 200 is confirmed or a 10-second timeout expires.
5. **Window Initialization & In-Memory Token Injection**:
   - `pywebview.create_window` opens a native window using Microsoft Edge WebView2.
   - The session token is injected directly into JavaScript window memory through `webview`'s host API. The token is never exposed in URLs, command-line arguments, or HTML source files.
6. **Graceful Shutdown**:
   - Closing the desktop window fires pywebview's `closing` event and Python `atexit` hooks, terminating the server thread and closing SQLite connections without leaving orphan processes.

---

## 3. Local Runtime Security

1. **Loopback Isolation**:
   - Waitress binds strictly to `127.0.0.1` (never `0.0.0.0` or external NICs). Windows Defender Firewall prompts are never triggered because loopback sockets are strictly local.
2. **Session Token Validation**:
   - `clinic.middleware.LoopbackSecurityMiddleware` intercepts every request to `/api/`.
   - Requests without a valid `X-Session-Token` matching the launch secret are rejected with `HTTP 403 Forbidden`.
   - Token comparisons use `hmac.compare_digest` to prevent timing attacks.
3. **CSRF Enforcement**:
   - Django’s CSRF protection is active for all state-changing endpoints (`POST`, `PATCH`), using standard double-submit cookie patterns.

---

## 4. Pure Service Layer Pattern

In accordance with system boundaries:
- **Views are Thin Adapters**: `clinic.views` only parses JSON, calls a service function, and maps returns to HTTP status codes.
- **Services are Pure Functions**: `clinic.services` contains all validation, database queries, and status transitions:
  - Validates models explicitly with `instance.full_clean()` before saving.
  - Executes writes within `transaction.atomic()`.
  - Never accepts or returns Django HTTP `Request` or `Response` objects.
  - Easily testable in pure unit tests without spin-up of HTTP servers.

---

## 5. Persistence & Storage Paths

- **Packaged / Production Mode**: `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`.
- **Test Mode**: In-memory SQLite or isolated temporary directories.
- **Performance & Concurrency**:
  - `PRAGMA journal_mode = WAL;` (Write-Ahead Logging) allows concurrent readers and writers without database locking errors on Windows.
  - `PRAGMA foreign_keys = ON;` strictly enforces referential integrity.
