# ScratchIQ Formula Reference

## Table of Contents
1. Total Tickets Printed
2. Estimated Remaining Tickets
3. Current Live Odds
4. Tax-Adjusted Net Prize Value
5. Expected Value
6. EV Per Dollar
7. Win Probability
8. Top Prize Concentration Score
9. Budget Optimizer
10. Exclusion Filters

---

## 1. Total Tickets Printed

Use the highest-volume prize tier as the anchor. "Highest-volume" means the tier with the most total prizes (typically the lowest prize amount like $2 or $5).

```
total_tickets = odds × total_prizes
```

Where:
- `odds` = the 1-in-X odds for that tier (use X, not 1/X)
- `total_prizes` = total number of prizes at that tier

**Cross-validation**: Calculate `total_tickets` from 2-3 different tiers. They should agree within ~5%. If they diverge, flag it — it may indicate the game has multiple play styles or the data has errors.

**Example**: If $5 prize tier has odds 1-in-4.5 and 1,000,000 total prizes:
```
total_tickets = 4.5 × 1,000,000 = 4,500,000
```

## 2. Estimated Remaining Tickets

Pick the highest-volume **mid-tier** prize ($10–$50 range) as the depletion proxy.

Why mid-tier:
- Bottom tier ($2–$5): Many winners never redeem small prizes → remaining count is artificially high → overestimates tickets remaining
- Top tier ($500+): Too few prizes → small sample → noisy estimate
- Mid tier ($10–$50): High enough that people redeem, numerous enough for stable statistics

```
pct_remaining = remaining_prizes / total_prizes    (for chosen anchor tier)
remaining_tickets = total_tickets × pct_remaining
```

## 3. Current Live Odds Per Tier

```
current_odds[tier] = remaining_tickets / remaining_prizes[tier]
```

This reflects the actual current odds, not the printed odds. If a tier's prizes have been claimed faster than average, its current odds will be worse (higher number) than printed.

## 4. Tax-Adjusted Net Prize Value

NC tax withholding on prizes > $600:
- State: 5.25%
- Federal: 24%
- Combined: 29.25%
- Net multiplier: 0.7075

```
if prize > 600:
    net_value = prize × 0.7075
else:
    net_value = prize
```

Note: Prizes ≤ $600 are still taxable income, but NC doesn't withhold at point of sale. The EV calculation uses net (post-withholding) values because that's what the player actually receives.

## 5. Expected Payout Per Ticket

```
EV = Σ ( net_value[tier] × remaining_prizes[tier] / remaining_tickets )
```

This sums across all prize tiers. Each term represents: (what you'd get paid) × (probability of winning that tier).

`EV` here means **expected payout per ticket**, not expected profit. If you want expected profit, compute:

```
net_ev = EV - ticket_price
```

## 6. EV Per Dollar

```
ev_per_dollar = EV / ticket_price
```

This is the **primary ranking metric**. An ev_per_dollar of 0.70 means you expect to get back $0.70 for every $1 spent. Higher is better. Above 1.0 would be a positive expected value (rare but possible in depleted pools with remaining top prizes).

## 7. Win Probability (Any Prize)

```
p_win = Σ ( remaining_prizes[tier] / remaining_tickets )
```

This is the probability of winning *something* on a single ticket. Useful for the user's gut-feel comparison between games.

For buying multiple tickets of the same game:

```
p_any_win_for_selection = 1 − (1 − p_win)^count
```

## 8. Top Prize Concentration Score

```
top_concentration = (top_remaining / top_total) / (mid_remaining / mid_total)
```

Interpretation:
- **> 1.0**: Top prizes have been claimed at a slower rate than mid-tier prizes. The top-prize pool is proportionally richer than at launch. **Favorable signal.**
- **= 1.0**: Top prizes depleted at the same rate as mid-tier. Neutral.
- **< 1.0**: Top prizes depleted faster than mid-tier. The remaining pool is top-prize-poor. **Unfavorable.**

Use the same mid-tier anchor you used for the remaining tickets estimate.

## 9. Budget Optimizer

For normal scratch-off budgets, treat this as a bounded integer optimization problem rather than a greedy fill:

```
maximize Σ (count_i × EV_i)
subject to Σ (count_i × ticket_price_i) ≤ budget
where each count_i is a non-negative integer
```

Use `ev_per_dollar` as the primary ranking metric and tie-breaker, but do not claim a greedy allocation is always optimal for mixed ticket prices.

Per selection:

```
selection_spend = count × ticket_price
selection_expected_payout = count × EV
selection_p_top_prize = 1 − (1 − 1/current_top_odds)^count
selection_p_any_win = 1 − (1 − p_win)^count
```

Across the full buy list:

```
total_expected_payout = Σ selection_expected_payout
overall_p_any_win = 1 − Π (1 − p_win_i)^count_i
overall_p_top_prize = 1 − Π (1 − 1/current_top_odds_i)^count_i
```

## 10. Exclusion Filters

Apply these before ranking. Remove any game where:

1. **All top prizes claimed**: No jackpot remaining. The EV takes a significant hit without the top tier.
2. **pct_remaining < 15%**: The ticket pool is nearly exhausted. The data becomes unreliable at low remaining counts, and stores may have stale inventory.
3. **ticket_price > budget**: Can't afford even one ticket.
