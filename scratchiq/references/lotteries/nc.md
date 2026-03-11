# North Carolina Education Lottery

## Data Source

```
URL: https://nclottery.com/scratch-off-prizes-remaining
```

Parse the full prize table for every active scratch-off game. The page contains a table per game with: game name, game number (3-digit), ticket price, and per prize tier: prize amount, odds (1-in-X), total prizes, prizes remaining.

## Tax Rules

NC withholds on prizes over $600:

- State tax: 5.25%
- Federal tax: 24%
- Combined withholding: 29.25%
- Net multiplier: 0.7075

```
net_value = prize > 600 ? prize × 0.7075 : prize
```

## Game Identification

NC scratch-off games use a 3-digit game number (e.g., 901, 845). When matching photos to live data, the game number is the most reliable identifier. Game names and ticket artwork/colors can help with partial matches.

## Notes

- NC lottery data updates roughly daily
- Some games may appear on the site after all top prizes are claimed — the exclusion filter handles this
- The prizes-remaining page is the single source of truth; do not use other pages or cached data
- The current page structure is organized around scratch-off `databox` containers keyed by `price_*` CSS classes; parsers should target those blocks rather than generic page headers/tables
- If the fetch succeeds but no valid game records can be parsed, fail closed and tell the user live data could not be parsed
