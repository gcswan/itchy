"""Direct import of the itchy fetcher for EV metric snapshots."""

import sys
from pathlib import Path

# Add repo root to sys.path so we can import itchy.scripts.fetch_nc_data
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from itchy.scripts.fetch_nc_data import fetch_and_parse, compute_ev_metrics


def get_current_rankings() -> dict:
    """Fetch live data and compute EV metrics. Returns the full rankings dict."""
    data = fetch_and_parse()
    return compute_ev_metrics(data["games"])


def lookup_game(rankings: dict, game_number: int) -> dict | None:
    """Find a specific game's metrics from a rankings result."""
    for entry in rankings.get("rankings", []):
        if entry["game_number"] == game_number:
            return entry
    return None
