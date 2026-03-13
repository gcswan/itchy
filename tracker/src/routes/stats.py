"""Aggregate stats routes."""

from decimal import Decimal

from fastapi import APIRouter

from src.db import get_conn

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _dec(v):
    return float(v) if isinstance(v, Decimal) else v


@router.get("/summary")
def summary():
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) AS total_purchases,
            COALESCE(SUM(ticket_price), 0) AS total_spent,
            COALESCE(SUM(amount_won), 0) AS total_won,
            COALESCE(SUM(amount_won) - SUM(ticket_price), 0) AS net_pl,
            COUNT(*) FILTER (WHERE amount_won IS NOT NULL AND amount_won > 0) AS wins,
            COUNT(*) FILTER (WHERE amount_won IS NOT NULL) AS scratched,
            COALESCE(AVG(ev_per_dollar) FILTER (WHERE ev_per_dollar IS NOT NULL), 0)
                AS avg_ev_per_dollar
        FROM purchases
    """).fetchone()

    total_purchases, total_spent, total_won, net_pl, wins, scratched, avg_ev = row
    win_rate = wins / scratched if scratched > 0 else 0
    actual_return_rate = float(total_won) / float(total_spent) if total_spent > 0 else 0

    return {
        "total_purchases": total_purchases,
        "total_spent": _dec(total_spent),
        "total_won": _dec(total_won),
        "net_pl": _dec(net_pl),
        "wins": wins,
        "scratched": scratched,
        "unscratched": total_purchases - scratched,
        "win_rate": round(win_rate, 4),
        "avg_ev_per_dollar": round(_dec(avg_ev), 4),
        "actual_return_rate": round(actual_return_rate, 4),
    }


@router.get("/by-game")
def by_game():
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            game_number,
            game_name,
            COUNT(*) AS count,
            SUM(ticket_price) AS total_spent,
            COALESCE(SUM(amount_won), 0) AS total_won,
            COALESCE(SUM(amount_won) - SUM(ticket_price), 0) AS net_pl,
            COUNT(*) FILTER (WHERE amount_won IS NOT NULL AND amount_won > 0) AS wins,
            COALESCE(AVG(ev_per_dollar) FILTER (WHERE ev_per_dollar IS NOT NULL), 0)
                AS avg_ev_per_dollar
        FROM purchases
        GROUP BY game_number, game_name
        ORDER BY net_pl DESC
    """).fetchall()

    cols = (
        "game_number", "game_name", "count", "total_spent",
        "total_won", "net_pl", "wins", "avg_ev_per_dollar",
    )
    return [
        {k: round(_dec(v), 4) if isinstance(v, (Decimal, float)) else v for k, v in zip(cols, r)}
        for r in rows
    ]
