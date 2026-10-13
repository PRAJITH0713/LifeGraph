# LifeGraph

LifeGraph is a privacy-first citizen service orchestration starter. It contains a Flask server, a bilingual static-style frontend, a SQLite catalogue, and clearly marked demo service data. Catalogue guidance is informational: official proof requirements and service-centre listings are not yet verified.

## Project layout

- `backend/`: Flask application, routes, services, database helpers, and demo JSON data.
- `frontend/`: English/Tamil pages, CSS, and JavaScript.
- `uploads/`: ignored legacy upload files. Existing files here have no verified account owner and are not served.
- `backend/instance/uploads/`: private storage for new uploads by default; outside the public static directory and ignored by Git.
- `backend/instance/lifegraph.db`: default SQLite database; ignored by Git.

## Requirements and setup

Python 3.10 or newer and pip are required. From the repository root:

```powershell
if (-not (Test-Path -LiteralPath .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

The `.env` copy is optional for local defaults. The guard preserves an existing `.env`; do not replace an existing configuration with `.env.example`. Start the existing app from `backend/` so the example's relative database path resolves to `backend/instance/lifegraph.db`:

```powershell
Set-Location D:\LifeGraph\backend
..\.venv\Scripts\python.exe app.py
```

The default local URL is `http://127.0.0.1:5000`. Startup initializes or additively migrates the SQLite schema; it does not reset the database. Keep `backend/instance/lifegraph.db` and any existing `.env` in place. The `.env.example` values use local-development defaults.

## Authentication and private data

Create an account at `/signup`; log in, log out, and request password resets at `/login`, `/logout`, and `/forgot-password`. The `/dashboard`, `/service`, and `/checklist` pages are private, as are `/api/services/...`, `/api/documents/...`, `/api/checklists/...`, and `/api/auth/me`. The public pages are the landing page (`/`), authentication/reset pages, and the demo centre information page (`/map`); `/api/health` is a public health check. Unauthenticated page requests go to login with a safe local return target, while private API calls return 401 JSON.

Passwords are hashed with Argon2id. The app uses signed Flask sessions, HttpOnly and SameSite=Lax session cookies, CSRF protection on browser forms and state-changing APIs, and rate limits on signup, login, and reset requests. New accounts require a unique normalized email. A password reset increments an authentication version to invalidate existing sessions.

For local development, the app generates a process-local Flask secret when `LIFEGRAPH_SECRET_KEY` is unset; this is not suitable for deployment and sessions will not survive restarts. Before deployment, supply a stable, securely managed `LIFEGRAPH_SECRET_KEY` and set `LIFEGRAPH_COOKIE_SECURE=true` behind HTTPS. No production secret or deployment configuration is included in this repository. The default limiter backend is `memory://`; configure `LIFEGRAPH_RATE_LIMIT_STORAGE_URI` to shared Redis when running multiple app processes.

Password-reset responses do not disclose whether an email exists. Email delivery requires `LIFEGRAPH_MAIL_SERVER`, `LIFEGRAPH_MAIL_PORT` (STARTTLS), `LIFEGRAPH_MAIL_USERNAME`, `LIFEGRAPH_MAIL_PASSWORD`, `LIFEGRAPH_MAIL_SENDER`, and a trusted HTTPS `LIFEGRAPH_PUBLIC_URL`. Until these are configured, the app does not issue a usable reset token; it logs that delivery is unavailable. Email verification is not implemented.

## Database migration and existing uploads

Before applying the additive authentication schema to an existing SQLite database, startup creates a timestamped backup beside it:

```text
<database>.pre-auth-<UTC timestamp>.bak
```

The migration adds user, document, and checklist-progress tables; it does not delete or convert existing catalogue records. Existing catalogue rows remain shared demo data. Existing files in the old root `uploads/` folder are left untouched but are not attached to an account, listed, or downloadable. An operator must decide whether to retain or remove these legacy orphaned files. Old browser-local checklist progress is not imported because it has no verified account owner. Database backups, instance data, environment files, and upload files are excluded from Git.

New uploads are limited to PDF, PNG, JPG, or JPEG files and 10 MB, validated against file signatures, and assigned server-generated storage names. The dashboard allows the authenticated owner to list, download, and delete their files. Every private document query filters by the authenticated session's user ID. Files are not OCR-processed, analyzed, or sent to external services.

Checklist progress is stored server-side by authenticated user, service, checklist type, and item index. The selected catalogue service and language preference remain in browser storage.

The Centre Finder is an unavailable-state page, not a functioning search or map. The official e-Sevai portal describes visiting a nearby e-Sevai centre, but LifeGraph has not verified a public centre directory/API for it. The remaining catalogue services belong to separate authorities and may use separate centre networks. A current, approved source and coverage details are required per supported network before adding centre search; no centre names, addresses, coordinates, hours, maps, or directions are fabricated.

## Demo walkthrough and readiness

Use a dedicated demo account and synthetic documents only; do not upload real personal documents. Select the supplied synthetic `lifegraph-download-check.pdf` for the upload demonstration.

1. Log in, then show the dashboard.
2. Open **Services**, choose a demo service, and open its checklist.
3. Check a planning reminder or checklist item. Reload the page and confirm the saved state remains.
4. Return to the dashboard, use the document upload control to select the synthetic PDF, and upload it. Click its filename in **Your Documents** to download it.
5. Switch the language picker to Tamil and back to English.
6. Use **Log out** and confirm the private workspace returns to the login screen.

Before a live demo, confirm the intended demo account can log in, the local server responds on port 5000, and the synthetic PDF upload/download works in the presentation browser. All 33 catalogue entries are demo data; their requirement status is `needs_verification`. Tamil service-name and description translations are unverified. Do not present the catalogue as official guidance or rely on its requirements.

External connections are limited to outbound links to official/department portals and optional SMTP password-reset delivery when configured. There is no centre search, map, geocoding, centre-directory API, OCR, document analysis, or document upload to a third party. Password-reset email requires the SMTP variables and trusted HTTPS `LIFEGRAPH_PUBLIC_URL` listed above; it is not configured by default. Verify any service requirements and availability directly with the relevant authority.

## Services, language, and APIs

The catalogue contains 33 clearly marked demo entries: 16 Tamil Nadu e-Sevai certificate names and 17 “Everyday Government Services” examples. All 33 currently have unverified requirement status. Service links point to department portals; they do not imply every listed task is available through e-Sevai. No official document rules are claimed. The interface supports English and Tamil; displayed Tamil service-name and description translations are marked unverified.

Authenticated catalogue/workflow APIs:

- `GET /api/services` (optional `q`, at most 100 characters)
- `GET /api/services/<service_id>`
- `GET /api/services/<service_id>/checklist` (catalogue information only)

Authenticated APIs:

- `GET /api/auth/me`
- `GET /api/documents`
- `POST /api/documents/upload`
- `GET /api/documents/<document_id>` (attachment download after ownership check)
- `DELETE /api/documents/<document_id>` (owner-only)
- `GET` and `PUT /api/checklists/<service_id>` (private checklist progress)

Open `/api/health` for the health response. Run tests from `backend/` with:

```powershell
python -m unittest discover -s ..\tests -v
```

## Remaining security work

This implementation is not a claim of production security. Email verification, self-service account deletion/data export, malware scanning, a retention/audit policy, and multi-process shared rate-limit storage are not implemented by default. Before internet-facing deployment, configure HTTPS, a stable secret, shared limiter storage, appropriate reverse-proxy and host settings, protected database/upload backups, monitoring, dependency-update practices, and incident/retention procedures. The automatic pre-migration copy is a safety measure, not a replacement for managed backups or restore testing.
