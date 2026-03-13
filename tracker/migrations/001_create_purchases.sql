CREATE TABLE IF NOT EXISTS purchases (
    id              SERIAL PRIMARY KEY,
    game_number     INTEGER NOT NULL,
    game_name       TEXT NOT NULL,
    ticket_price    NUMERIC(6,2) NOT NULL,
    store_name      TEXT,
    store_location  TEXT,
    ticket_number   TEXT,
    purchased_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount_won      NUMERIC(10,2),
    ev_per_dollar       NUMERIC(8,6),
    top_concentration   NUMERIC(8,6),
    pct_remaining       NUMERIC(8,6),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchases_game_number ON purchases(game_number);
CREATE INDEX IF NOT EXISTS idx_purchases_purchased_at ON purchases(purchased_at);
