# LifeGraph

LifeGraph is a privacy-first citizen service orchestration project. This repository contains an intentionally small starter skeleton: a Flask server, a static multi-page frontend, SQLite initialization, and clearly marked demo data. It does not provide official requirements, document processing, centre search, routing, or service advice.

## Project layout

- `backend/`: Flask application, environment configuration, API route placeholders, modular service placeholders, SQLite helpers, and demo JSON data.
- `frontend/`: Static HTML pages, shared CSS, and JavaScript for navigation and API status.
- `uploads/`: Private local storage for accepted document uploads; ignored by Git and not served as static files.
- `requirements.txt`: Python dependencies for the backend.
- `.env.example`: Example local configuration; copy it to `.env` to customize settings.

The Tamil Nadu e-Sevai certificate names in `backend/data/services.json` were checked against its directory on 2026-10-05. An additional “Everyday Government Services” category links to the relevant central and Tamil Nadu portals. Catalogue descriptions and service routing are informational; service-specific proof requirements have not been confirmed or included. No service-centre listings are verified.

## Requirements

- Python 3.10 or newer
- pip

## Install dependencies

From the project root, create and activate a virtual environment, then install the listed packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

To use custom settings, copy `.env.example` to `.env` in the project root and edit it. The defaults work without a `.env` file.

## Start the Flask server

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python app.py
```

The server starts at `http://127.0.0.1:5000`. SQLite is initialized automatically at `backend/instance/lifegraph.db` the first time the app loads.

## Services and checklists

Open `/service` to browse the 16 names listed in the official [Tamil Nadu e-Sevai service directory](https://tnesevai.tn.gov.in/Pages/EsevaiServiceList.aspx) and 17 distinct Everyday Government Services entries covering licence, PAN, voter, passport, birth/death/marriage, ration-card, Aadhaar, and vehicle-RC guidance (33 catalogue entries total). Everyday entries link to their responsible department's official portal; this does not imply e-Sevai provides those services. Official portals confirm entry points, not necessarily every document rule. No service currently has a source-confirmed requirements list in this catalogue, so each shows “Needs verification” and a portal link rather than invented checklist items. The checklist page keeps any available checkbox progress and planning reminders in browser local storage, keyed by service ID, and restores the selected service across refreshes.

Catalogue endpoints are `GET /api/services`, `GET /api/services/<service_id>`, and `GET /api/services/<service_id>/checklist`. Search uses the optional `q` parameter and accepts up to 100 characters. `POST /api/documents/upload` accepts one PDF, PNG, JPG, or JPEG file up to 10 MB in the `document` multipart field. Uploads are signature-checked and stored under the ignored local `uploads/` directory using generated filenames; they are not downloadable through the app and are not scanned, OCR-processed, or otherwise analyzed. Uploaded files stay on disk until an operator removes them.

## Language support

The interface defaults to English and can be switched to Tamil from the page header. The selection is stored in this browser and follows navigation and refreshes. Tamil service-name and description text is marked as unverified demo translation; official proof requirements remain unmodified and are shown in their source language until a translation is verified.

## Test the health endpoint

Open `http://127.0.0.1:5000/api/health` in a browser, or run this in PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

A healthy response is:

```json
{"application":"LifeGraph","status":"ok"}
```

## Open the frontend

With the Flask server running, open `http://127.0.0.1:5000/`. The dashboard, service area, checklist, and centre pages are available from the navigation at `/dashboard`, `/service`, `/checklist`, and `/map`.
