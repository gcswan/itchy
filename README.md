# Itchy

A Claude Code skill that acts as a real-time NC scratch-off lottery ticket advisor. It fetches live prize data from the NC Education Lottery, calculates expected value, and recommends optimal ticket purchases.

## Install

Copy the `itchy` directory into your Claude Code personal skills folder

```bash
cp -r itchy ~/.claude/skills/itchy
```

Claude Code picks up skills automatically — no restart needed. You can verify it's loaded by starting a new conversation and checking that `itchy` appears in the available skills list.

## Usage

Just ask about NC scratch-off tickets in any Claude Code session:

- "Which scratch-off should I buy?"
- "I have $20 to spend on scratch-offs"
- Share a photo of a store's scratch-off display

ScratchIQ will fetch live prize data, run EV math, and give you a purchase recommendation.

## Structure

```
itchy/
├── SKILL.md          # Main skill definition
├── references/       # Formulas and lottery-specific data
├── scripts/          # Data fetching utilities
├── evals/            # Test prompts
└── tests/            # Unit tests
```
