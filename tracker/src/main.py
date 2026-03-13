"""FastAPI entry point for the scratch-off purchase tracker."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.db import get_conn, close
from src.migrate import run_migrations
from src.routes.purchases import router as purchases_router
from src.routes.stats import router as stats_router
from src.services.ev_fetcher import get_current_rankings

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_conn()
    applied = run_migrations(conn)
    if applied:
        log.info("Applied migrations: %s", applied)
    else:
        log.info("No pending migrations")
    yield
    close()


app = FastAPI(title="Itchy Tracker", lifespan=lifespan)

app.include_router(purchases_router)
app.include_router(stats_router)


@app.get("/api/ev/current")
def current_ev():
    """Proxy to the Python fetcher — returns live EV rankings."""
    return get_current_rankings()


# Serve the static UI
static_dir = Path(__file__).parent / "public"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
