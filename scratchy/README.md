# Scratchy

Scratch-off purchase tracker with a FastAPI backend, a static web UI, and a
Postgres database.

## What Runs Where

- FastAPI app: serves the API and the browser UI on `http://localhost:8000`
- Postgres: runs on `localhost:5434` via Docker Compose
- Database schema: applied automatically when the app starts

## Prerequisites

- Python 3.10+
- `uv` installed, or another way to create a Python environment and install the
  package
- Docker Desktop or Docker Engine

## Quick Start

From the repo root:

```bash
cd scratchy
docker compose up -d
uv sync
uv run scratchy
```

Then open:

- App UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

The app will connect to Postgres using the default local database URL:

```bash
postgres://itchy:itchy@localhost:5434/scratchy
```

## Running Without `uv`

If you prefer plain `pip`:

```bash
cd scratchy
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -e .
scratchy
```

## Environment Variables

You can override the database connection with `DATABASE_URL`:

```bash
export DATABASE_URL=postgres://itchy:itchy@localhost:5434/scratchy
```

If `DATABASE_URL` is not set, the app uses that local default automatically.

## Stopping Everything

Stop the app process with `Ctrl+C`.

Stop Postgres with:

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## Troubleshooting

- If `uv run scratchy` fails to connect to Postgres, make sure `docker compose up -d`
  succeeded and port `5434` is free.
- If dependencies are missing, rerun `uv sync`.
- If the UI loads but live EV data fails, the tracker can still store purchases,
  but the EV snapshot fields may be empty until the fetch succeeds.
