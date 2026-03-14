---
name: scratchy
description: Analyze a photo of a scratched lottery ticket, extract game info and results, and log the purchase to the scratchy API. Use this skill whenever the user provides a photo of a scratch-off ticket and wants to log, ingest, scan, record, or track it. Also trigger when the user says "ingest ticket", "log this ticket", "add this scratch off", "scan this ticket", or any variation of recording a scratched ticket's results. Even casual phrasing like "here's my ticket" with a photo should trigger this skill.
---

# Scratchy - Scratch-Off Ticket Photo Ingestion

You are analyzing a photo of a scratched lottery scratch-off ticket to extract its metadata and results, then logging it as a purchase in the scratchy API. The goal is to make ticket logging effortless — the user just snaps a photo and you handle the rest.

## Step 1: Read the Ticket Photo

Use Claude's vision capabilities to carefully examine the ticket image. Texas Lottery scratch-off tickets have a standard layout, but other states follow similar patterns. Look for these elements:

**Required fields:**
- **Game number** — Usually a small integer (e.g., 2345) printed near the top or bottom of the ticket, often preceded by "Game #" or "No."
- **Game name** — The title of the game, prominently displayed (e.g., "MILLION DOLLAR JACKPOT", "LUCKY 7S")
- **Ticket price** — Printed on the ticket, common values: $1, $2, $3, $5, $10, $20, $30, $50

**Optional fields:**
- **Ticket number / serial number** — A long alphanumeric code, often near the barcode at the bottom or back of the ticket. May be labeled "Ticket No." or just printed below the barcode
- **Store name** — Sometimes printed on the ticket or visible on a receipt attached to/near the ticket
- **Store location** — City/address if visible

**Result determination:**
- **Winner or loser** — Examine the scratched play area. The specific game mechanics vary, but look for:
  - Matching numbers/symbols that indicate a prize
  - "WIN" or prize amounts revealed in the play area
  - If all play areas are scratched and no winning combination is visible, it's a loser ($0)
- **Prize amount** — If it's a winner, identify the dollar amount won. This is usually printed in the winning area of the ticket

If any required field is unclear or unreadable, note what you can't determine and ask the user to fill in the gap.

## Step 2: Present Extracted Info for Confirmation

Before submitting anything, show the user what you found in a clear format:

```
Here's what I extracted from your ticket:

  Game:       #2345 - MILLION DOLLAR JACKPOT
  Price:      $10
  Ticket #:   1234567890
  Result:     Winner - $20
  Store:      (not visible)

Does this look right? I'll log it to the scratchy API once you confirm.
```

If you're uncertain about any field, flag it clearly (e.g., "Game number looks like 2345 but it's partially obscured — can you confirm?").

Wait for the user to confirm or correct before proceeding. If they provide corrections, update accordingly.

## Step 3: Submit to Scratchy API

Once confirmed, POST the purchase to the scratchy API using curl or a similar tool:

```bash
curl -s -X POST http://localhost:8000/api/purchases \
  -H "Content-Type: application/json" \
  -d '{
    "game_number": <int>,
    "game_name": "<string>",
    "ticket_price": <decimal>,
    "store_name": <string or null>,
    "store_location": <string or null>,
    "ticket_number": <string or null>,
    "purchased_at": null,
    "amount_won": <decimal or null>
  }'
```

Field notes:
- `game_number` must be an integer
- `ticket_price` is the cost (e.g., 10.00 for a $10 ticket)
- `amount_won` should be:
  - `0` for a losing ticket (scratched, no win)
  - The prize amount for a winner (e.g., `20.00`)
  - `null` only if the ticket hasn't been scratched yet
- `purchased_at` can be `null` (defaults to now) or an ISO 8601 datetime if the user specifies when they bought it
- `store_name` and `store_location` are `null` if not visible on the ticket
- `ticket_number` is `null` if not legible

## Step 4: Confirm Success

After a successful POST (HTTP 201), show the user the key details from the response:

```
Logged! Purchase #42:
  Game:       #2345 - MILLION DOLLAR JACKPOT
  Spent:      $10.00
  Won:        $20.00
  Net:        +$10.00
  EV/Dollar:  0.7823
```

If the response includes an `ev_warning`, mention it (e.g., "Note: EV data wasn't available at the time of logging").

If the POST fails, show the error and suggest the user check that the scratchy API is running (`docker compose up -d && uv run scratchy` from the scratchy directory).

## Handling Multiple Tickets

If the user provides photos of multiple tickets at once, process each one individually. Present all extracted data together for batch confirmation, then submit them one at a time. Show a summary at the end:

```
Logged 3 tickets:
  #1: #2345 MILLION DOLLAR JACKPOT — Lost ($10)
  #2: #1890 LUCKY 7S — Won $5 ($2 ticket, net +$3)
  #3: #2100 CASH BLAST — Won $50 ($5 ticket, net +$45)

Session total: Spent $17, Won $55, Net +$38
```

## Edge Cases

- **Unscratched ticket**: If the play area hasn't been scratched, set `amount_won` to `null` and note this to the user
- **Partially scratched**: Ask the user if they want to log it as unscratched (null) or if they can tell the result
- **Blurry/unreadable**: Ask the user to provide the missing info rather than guessing
- **Non-Texas tickets**: The skill works for any state's scratch-offs — the fields are universal
