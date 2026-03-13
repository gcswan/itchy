"""CRUD routes for scratch-off purchases."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db import get_conn
from src.services.ev_fetcher import get_current_rankings, lookup_game

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


class PurchaseCreate(BaseModel):
    game_number: int
    game_name: str
    ticket_price: Decimal
    store_name: str | None = None
    store_location: str | None = None
    ticket_number: str | None = None
    purchased_at: datetime | None = None
    amount_won: Decimal | None = None


class PurchaseUpdate(BaseModel):
    amount_won: Decimal | None = None
    store_name: str | None = None
    store_location: str | None = None
    ticket_number: str | None = None


def _row_to_dict(row, cols):
    d = dict(zip(cols, row))
    d["net_profit"] = (
        float(d["amount_won"] - d["ticket_price"])
        if d["amount_won"] is not None
        else None
    )
    # Convert Decimals to float for JSON serialization
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
    return d


COLUMNS = (
    "id", "game_number", "game_name", "ticket_price",
    "store_name", "store_location", "ticket_number",
    "purchased_at", "amount_won",
    "ev_per_dollar", "top_concentration", "pct_remaining",
    "created_at", "updated_at",
)
SELECT_COLS = ", ".join(COLUMNS)


@router.get("")
def list_purchases(limit: int = 50, offset: int = 0, game_number: int | None = None):
    conn = get_conn()
    if game_number is not None:
        rows = conn.execute(
            f"SELECT {SELECT_COLS} FROM purchases WHERE game_number = %s "
            "ORDER BY purchased_at DESC LIMIT %s OFFSET %s",
            (game_number, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {SELECT_COLS} FROM purchases "
            "ORDER BY purchased_at DESC LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
    return [_row_to_dict(r, COLUMNS) for r in rows]


@router.get("/{purchase_id}")
def get_purchase(purchase_id: int):
    conn = get_conn()
    row = conn.execute(
        f"SELECT {SELECT_COLS} FROM purchases WHERE id = %s", (purchase_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return _row_to_dict(row, COLUMNS)


@router.post("", status_code=201)
def create_purchase(body: PurchaseCreate):
    ev_per_dollar = None
    top_concentration = None
    pct_remaining = None
    ev_warning = None

    try:
        rankings = get_current_rankings()
        game = lookup_game(rankings, body.game_number)
        if game:
            m = game["metrics"]
            ev_per_dollar = m["ev_per_dollar"]
            top_concentration = m["top_concentration"]
            pct_remaining = m["pct_remaining"]
    except Exception as e:
        ev_warning = f"EV snapshot failed: {e}"

    purchased_at = body.purchased_at or datetime.now(timezone.utc)

    conn = get_conn()
    row = conn.execute(
        f"""
        INSERT INTO purchases (
            game_number, game_name, ticket_price,
            store_name, store_location, ticket_number,
            purchased_at, amount_won,
            ev_per_dollar, top_concentration, pct_remaining
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {SELECT_COLS}
        """,
        (
            body.game_number, body.game_name, body.ticket_price,
            body.store_name, body.store_location, body.ticket_number,
            purchased_at, body.amount_won,
            ev_per_dollar, top_concentration, pct_remaining,
        ),
    ).fetchone()

    result = _row_to_dict(row, COLUMNS)
    if ev_warning:
        result["ev_warning"] = ev_warning
    return result


@router.patch("/{purchase_id}")
def update_purchase(purchase_id: int, body: PurchaseUpdate):
    conn = get_conn()

    existing = conn.execute(
        "SELECT id FROM purchases WHERE id = %s", (purchase_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Purchase not found")

    updates = []
    values = []
    for field in ("amount_won", "store_name", "store_location", "ticket_number"):
        val = getattr(body, field, None)
        if val is not None:
            updates.append(f"{field} = %s")
            values.append(val)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    values.append(purchase_id)

    row = conn.execute(
        f"UPDATE purchases SET {', '.join(updates)} WHERE id = %s RETURNING {SELECT_COLS}",
        values,
    ).fetchone()

    return _row_to_dict(row, COLUMNS)


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int):
    conn = get_conn()
    result = conn.execute(
        "DELETE FROM purchases WHERE id = %s", (purchase_id,)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Purchase not found")
