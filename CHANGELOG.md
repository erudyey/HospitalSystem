# Changelog

## v0.1.0

- Add role-based receptionist and doctor workspaces, booking and check-in,
  consultation notes, and patient charts.
- Keep demo data shared across staff accounts and preserve it across account
  switches and restarts. Explicit logout leaves the user signed out.
- Protect completed visits and clinical records, validate schedule conflicts,
  and isolate verification from the user's clinic database.
- Add a staff welcome banner and consistent summary cards with clear date and
  lifetime scopes. Date filters include both endpoints.
- Add daily reports with doctor-specific access, distinct patient counts,
  live refresh, and snapshot CSV export through native Save or browser download.
- Add teal navigation, blue information accents, amber demo indicators, and
  short transitions with reduced-motion support.
- Align package versions and release tags, retain the `Release vX.Y.Z` title
  format, and verify immutable release revisions before publishing both bundles
  with SHA-256 checksums.

Local checks cover 121 backend tests, 19 frontend tests, both required window
sizes, and isolated Windows bundle bootstrapping. Native Save interactions use
mocks with disposable file writes. The release workflow verifies macOS bundle
bootstrapping on its native runner; interactive macOS UI checks remain manual.
