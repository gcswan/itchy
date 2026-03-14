# Itchy

A Claude Code skill that acts as a real-time NC scratch-off lottery ticket
advisor. It fetches live prize data from the NC Education Lottery, calculates
expected value, and recommends optimal ticket purchases.

This repo also includes a separate scratch-off purchase tracker app in
`scratchy/`. For setup and run instructions, see [scratchy/README.md](scratchy/README.md).

## Install

Run the interactive installer:

```bash
bash install.sh
```

The script asks which CLI targets you want to install for and supports:

- Claude Code
- Gemini CLI
- Codex CLI

By default it installs via symlink so changes in this repo stay live. If you
want standalone copies instead, use:

```bash
bash install.sh --copy
```

## Usage

Just ask about NC scratch-off tickets in any Claude Code session:

- "Which scratch-off should I buy?"
- "I have $20 to spend on scratch-offs"
- Share a photo of a store's scratch-off display

ScratchIQ will fetch live prize data, run EV math, and give you a purchase
recommendation.

## Structure

```bash
itchy/
├── SKILL.md          # Main skill definition
├── references/       # Formulas and lottery-specific data
├── scripts/          # Data fetching utilities
├── evals/            # Test prompts
└── tests/            # Unit tests
```

## Scratchy

The scratchy app is a small FastAPI + Postgres project for logging purchases and
viewing stats.

Quick start:

```bash
cd scratchy
docker compose up -d
uv sync
uv run scratchy
```

Then open `http://localhost:8000`.
